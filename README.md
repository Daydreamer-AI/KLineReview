# KLineReview
一个基于akshare、baostock的股票数据处理和技术分析工具，自带回放复盘功能。

## 效果图

## 功能特点

- 获取股票历史数据
- 计算技术指标（MACD、MA等）
- 数据存储和管理
- 自定义指标计算
- k线回放复盘

## 安装
确保已安装 Python 3.10 或更高版本。

### 克隆代码到本地仓库

```bash
git clone ...
cd ...
```

### 创建并激活虚拟环境

venv:
```bash
cd ...
py -3.10 -m venv .venv
.venv\Scripts\activate
```

conda: 
```bash
conda create --name myenv python=3.10

conda activate myenv
```

### 安装依赖
```bash
pip install -r requirements.txt
```

## 使用示例

因使用本地数据，首次运行需手动下载数据。

执行数据下载脚本：
```bash
./scripts/run_baostock_data_update.bat
```


数据下载完成后，运行主程序
```bash
python ./src/main.py
```

## 文档

详细文档请参阅 [docs/](docs/) 目录。

## 贡献指南

欢迎提交问题和贡献代码，请参阅 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 许可证

本项目采用 MIT 许可证 - 详情请参阅 [LICENSE](LICENSE) 文件。

## 引用
### AKShare
AKShare 项目地址：https://github.com/akfamily/akshare


### Baostock
Baostock 项目地址：https://pypi.org/project/baostock/