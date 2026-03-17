# 第三方依赖声明

本项目使用了以下第三方开源项目作为数据采集组件：

## ToolBbrowser

- **项目地址**: https://github.com/epiral/bb-browser
- **作者**: @epiral
- **许可证**: 请参见原项目 LICENSE 文件
- **用途**: 浏览器自动化数据采集
- **集成方式**: 通过 CLI 调用，适配器位于 `rag_graph/collectors/adapters/toolbbrowser_adapter.py`

## Scrapling

- **项目地址**: https://github.com/D4Vinci/Scrapling
- **作者**: @D4Vinci
- **许可证**: 请参见原项目 LICENSE 文件
- **用途**: Python 爬虫框架
- **集成方式**: 通过 Python import 调用，适配器位于 `rag_graph/collectors/adapters/scrapling_adapter.py`

## 集成方式

这两个工具通过 **git submodule** 集成到本项目中：

1. 克隆本项目时添加 `--recursive` 参数可自动下载
2. 也可运行 `./setup-tools.sh` 脚本自动初始化并安装

详细安装说明请参见 README.md 的「第三方依赖」章节。

## 免责声明

- 本项目不拥有上述第三方项目的版权
- 使用这些工具时请遵守其各自的许可证条款
- 采集数据时请遵守相关网站的服务条款和 robots.txt 规定

## 免责声明

- 本项目不拥有上述第三方项目的版权
- 使用这些工具时请遵守其各自的许可证条款
- 采集数据时请遵守相关网站的服务条款和 robots.txt 规定
