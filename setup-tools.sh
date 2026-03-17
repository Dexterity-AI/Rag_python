#!/bin/bash
# ========================================
# GraphRAG 第三方采集工具安装脚本
# 使用 git submodule 管理第三方依赖
# ========================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  GraphRAG 第三方采集工具安装脚本${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 获取项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${YELLOW}项目根目录: $PROJECT_ROOT${NC}"
echo ""

# 检查命令是否存在
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# ========================================
# 检查 git submodule
# ========================================
check_submodules() {
    echo -e "${BLUE}[0/2] 检查 git submodule 配置...${NC}"

    cd "$PROJECT_ROOT"

    # 检查 .gitmodules 是否存在
    if [ ! -f ".gitmodules" ]; then
        echo -e "${YELLOW}  警告: .gitmodules 文件不存在${NC}"
        echo -e "${YELLOW}  请先运行以下命令添加 submodule:${NC}"
        echo ""
        echo "  git submodule add https://github.com/epiral/bb-browser.git ToolBbrowser"
        echo "  git submodule add https://github.com/D4Vinci/Scrapling.git Scrapling-main"
        echo ""
        return 1
    fi

    echo -e "${GREEN}  git submodule 配置已存在${NC}"
    echo ""
    return 0
}

# ========================================
# 初始化并更新 submodule
# ========================================
init_submodules() {
    echo -e "${BLUE}[初始化] 更新 git submodule...${NC}"

    cd "$PROJECT_ROOT"

    # 初始化并更新所有 submodule
    git submodule update --init --recursive

    echo -e "${GREEN}  Submodule 更新完成${NC}"
    echo ""
}

# ========================================
# 安装 ToolBbrowser
# ========================================
install_toolbbrowser() {
    echo -e "${BLUE}[1/2] 安装 ToolBbrowser...${NC}"

    TOOLBROWSER_DIR="$PROJECT_ROOT/ToolBbrowser"

    if [ ! -d "$TOOLBROWSER_DIR" ]; then
        echo -e "${RED}  错误: ToolBbrowser 目录不存在${NC}"
        echo -e "${YELLOW}  请确保 submodule 已正确配置${NC}"
        return 1
    fi

    cd "$TOOLBROWSER_DIR"

    # 检查 pnpm
    if ! command_exists pnpm; then
        echo -e "${YELLOW}  安装 pnpm...${NC}"
        npm install -g pnpm
    fi

    echo -e "${YELLOW}  安装依赖...${NC}"
    pnpm install

    echo -e "${YELLOW}  构建项目...${NC}"
    pnpm build

    echo -e "${GREEN}  ToolBbrowser 安装完成!${NC}"
    echo ""
}

# ========================================
# 安装 Scrapling
# ========================================
install_scrapling() {
    echo -e "${BLUE}[2/2] 安装 Scrapling...${NC}"

    SCRAPLING_DIR="$PROJECT_ROOT/Scrapling-main"

    if [ ! -d "$SCRAPLING_DIR" ]; then
        echo -e "${RED}  错误: Scrapling 目录不存在${NC}"
        echo -e "${YELLOW}  请确保 submodule 已正确配置${NC}"
        return 1
    fi

    cd "$SCRAPLING_DIR"

    echo -e "${YELLOW}  安装 Python 包...${NC}"
    pip install -e .

    echo -e "${GREEN}  Scrapling 安装完成!${NC}"
    echo ""
}

# ========================================
# 主程序
# ========================================
main() {
    # 检查依赖
    if ! command_exists git; then
        echo -e "${RED}错误: git 未安装${NC}"
        exit 1
    fi

    if ! command_exists node; then
        echo -e "${RED}错误: Node.js 未安装，请先安装 Node.js 18+${NC}"
        exit 1
    fi

    if ! command_exists pip; then
        echo -e "${RED}错误: pip 未安装${NC}"
        exit 1
    fi

    # 解析参数
    INSTALL_ALL=false
    INSTALL_TOOLB=false
    INSTALL_SCRAP=false
    SKIP_INIT=false

    if [ $# -eq 0 ]; then
        INSTALL_ALL=true
    else
        for arg in "$@"; do
            case $arg in
                --all)
                    INSTALL_ALL=true
                    ;;
                --toolbbrowser)
                    INSTALL_TOOLB=true
                    ;;
                --scrapling)
                    INSTALL_SCRAP=true
                    ;;
                --skip-init)
                    SKIP_INIT=true
                    ;;
                --help|-h)
                    echo "用法: $0 [选项]"
                    echo ""
                    echo "选项:"
                    echo "  --all          安装所有工具 (默认)"
                    echo "  --toolbbrowser 只安装 ToolBbrowser"
                    echo "  --scrapling    只安装 Scrapling"
                    echo "  --skip-init    跳过 submodule 初始化 (假设已存在)"
                    echo "  --help, -h     显示帮助"
                    echo ""
                    echo "说明:"
                    echo "  此脚本会自动使用 git submodule 下载并安装第三方工具。"
                    echo "  首次使用前需要确保 submodule 已添加到仓库。"
                    exit 0
                    ;;
                *)
                    echo -e "${RED}未知选项: $arg${NC}"
                    echo "使用 --help 查看帮助"
                    exit 1
                    ;;
            esac
        done
    fi

    # 检查 submodule 配置
    if ! $SKIP_INIT; then
        if ! check_submodules; then
            exit 1
        fi
        init_submodules
    fi

    # 执行安装
    if [ "$INSTALL_ALL" = true ] || [ "$INSTALL_TOOLB" = true ]; then
        install_toolbbrowser
    fi

    if [ "$INSTALL_ALL" = true ] || [ "$INSTALL_SCRAP" = true ]; then
        install_scrapling
    fi

    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  安装完成!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "第三方工具已通过 git submodule 集成到项目目录"
    echo ""
    echo "你可以运行以下命令验证安装:"
    echo "  python -c \"from rag_graph.collectors.adapters.toolbbrowser_adapter import ToolBbrowserAdapter; print('ToolBbrowser: OK')\""
    echo "  python -c \"from rag_graph.collectors.adapters.scrapling_adapter import ScraplingAdapter; print('Scrapling: OK')\""
}

main "$@"
