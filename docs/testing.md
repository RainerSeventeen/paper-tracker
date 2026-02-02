# 测试指南

本项目当前使用 `unittest` 作为测试框架，测试文件位于 `test/`。

## 运行测试

在项目根目录执行：

```bash
python -m unittest discover -s test -p "test_*.py"
```

## 测试配置

部分测试使用位于 `config/test/` 下的配置文件（例如启用 LLM 的配置）。

