# ai-autotest

## Python 版本约定

- 项目固定使用 `Python 3.11`（见 `.python-version`）。
- 推荐先安装 `pyenv`，再安装并切换 `3.11.x`。

## 环境初始化

```bash
pyenv install 3.11.11
pyenv local 3.11.11
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 运行示例

```bash
python llamaIndex_test.py
streamlit run streamlit_test.py
```
