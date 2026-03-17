import { copyFileSync, existsSync, unlinkSync } from "node:fs";
import { execSync } from "node:child_process";
import { homedir, tmpdir } from "node:os";
import { join } from "node:path";

export interface HistorySearchResult {
  url: string;
  title: string;
  visitCount: number;
  lastVisitTime: number;
}

export interface HistoryDomainResult {
  domain: string;
  visits: number;
  titles: string[];
}

function getHistoryPathCandidates(): string[] {
  const home = homedir();
  const localAppData = process.env.LOCALAPPDATA || "";
  const candidates: string[] = [
    join(home, "Library/Application Support/Google/Chrome/Default/History"),
    join(home, "Library/Application Support/Microsoft Edge/Default/History"),
    join(home, "Library/Application Support/BraveSoftware/Brave-Browser/Default/History"),
    join(home, "Library/Application Support/Arc/User Data/Default/History"),
    join(home, ".config/google-chrome/Default/History"),
  ];

  if (localAppData) {
    candidates.push(
      join(localAppData, "Google/Chrome/User Data/Default/History"),
      join(localAppData, "Microsoft/Edge/User Data/Default/History")
    );
  }

  return candidates;
}

function findHistoryPath(): string | null {
  for (const historyPath of getHistoryPathCandidates()) {
    if (existsSync(historyPath)) {
      return historyPath;
    }
  }
  return null;
}

function sqlEscape(value: string): string {
  return value.replace(/'/g, "''");
}

function buildTimeWhere(days?: number): string {
  if (!days || days <= 0) {
    return "";
  }

  return `last_visit_time > (strftime('%s', 'now') - ${Math.floor(days)}*86400) * 1000000 + 11644473600000000`;
}

function runHistoryQuery<T>(sql: string, mapRow: (row: string[]) => T | null): T[] {
  const historyPath = findHistoryPath();
  if (!historyPath) {
    return [];
  }

  const tmpPath = join(tmpdir(), `bb-history-${Date.now()}-${Math.random().toString(36).slice(2)}.db`);

  try {
    copyFileSync(historyPath, tmpPath);
    const escapedTmpPath = tmpPath.replace(/"/g, '\\"');
    const escapedSql = sql.replace(/"/g, '\\"');
    const output = execSync(`sqlite3 -separator $'\\t' "${escapedTmpPath}" "${escapedSql}"`, {
      encoding: "utf-8",
      stdio: ["pipe", "pipe", "pipe"],
    });

    return output
      .split("\n")
      .filter(Boolean)
      .map((line) => mapRow(line.split("\t")))
      .filter((item): item is T => item !== null);
  } catch {
    return [];
  } finally {
    try {
      unlinkSync(tmpPath);
    } catch {}
  }
}

export function searchHistory(query?: string, days?: number): HistorySearchResult[] {
  const conditions: string[] = [];
  const trimmedQuery = query?.trim();

  if (trimmedQuery) {
    const escapedQuery = sqlEscape(trimmedQuery);
    conditions.push(`(url LIKE '%${escapedQuery}%' OR title LIKE '%${escapedQuery}%')`);
  }

  const timeWhere = buildTimeWhere(days);
  if (timeWhere) {
    conditions.push(timeWhere);
  }

  const whereClause = conditions.length > 0 ? `WHERE ${conditions.join(" AND ")}` : "";
  const sql = `
    SELECT
      url,
      REPLACE(IFNULL(title, ''), char(9), ' '),
      IFNULL(visit_count, 0),
      IFNULL(last_visit_time, 0)
    FROM urls
    ${whereClause}
    ORDER BY last_visit_time DESC
    LIMIT 100;
  `.trim();

  return runHistoryQuery(sql, (row) => {
    if (row.length < 4) {
      return null;
    }

    const chromeTimestamp = Number(row[3]) || 0;
    return {
      url: row[0] || "",
      title: row[1] || "",
      visitCount: Number(row[2]) || 0,
      lastVisitTime: chromeTimestamp > 0 ? chromeTimestamp / 1000000 - 11644473600 : 0,
    };
  });
}

export function getHistoryDomains(days?: number): HistoryDomainResult[] {
  const timeWhere = buildTimeWhere(days);
  const whereClause = timeWhere ? `WHERE ${timeWhere}` : "";
  const sql = `
    SELECT
      domain,
      SUM(visit_count) AS visits,
      GROUP_CONCAT(title, char(31)) AS titles
    FROM (
      SELECT
        CASE
          WHEN instr(url, '//') > 0 AND instr(substr(url, instr(url, '//') + 2), '/') > 0
            THEN substr(
              substr(url, instr(url, '//') + 2),
              1,
              instr(substr(url, instr(url, '//') + 2), '/') - 1
            )
          WHEN instr(url, '//') > 0 THEN substr(url, instr(url, '//') + 2)
          WHEN instr(url, '/') > 0 THEN substr(url, 1, instr(url, '/') - 1)
          ELSE url
        END AS domain,
        IFNULL(visit_count, 0) AS visit_count,
        REPLACE(IFNULL(title, ''), char(31), ' ') AS title
      FROM urls
      ${whereClause}
    )
    WHERE domain != ''
    GROUP BY domain
    ORDER BY visits DESC
    LIMIT 50;
  `.trim();

  return runHistoryQuery(sql, (row) => {
    if (row.length < 3) {
      return null;
    }

    const titles = row[2]
      ? Array.from(new Set(row[2].split(String.fromCharCode(31)).map((title) => title.trim()).filter(Boolean))).slice(0, 10)
      : [];

    return {
      domain: row[0] || "",
      visits: Number(row[1]) || 0,
      titles,
    };
  });
}
