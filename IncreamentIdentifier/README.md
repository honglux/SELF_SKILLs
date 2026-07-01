# Excel 去重对比工具

## 用途

对比两个文件夹中的 Excel 文件，对第二个文件夹中的每一行标记其是否已在第一个文件夹中出现过。

## 输入

- **folder_a**：基准文件夹，包含多个 `.xlsx` 文件
- **folder_b**：待标记文件夹，包含多个 `.xlsx` 文件

两个文件夹路径通过**命令行参数**传入。

## 输出

- 输出文件夹自动在 **folder_b 同级目录**下创建，名称为 `<folder_b_name>_marked`
- 文件夹下生成与 `folder_b` 同名的 `.xlsx` 文件
- 每个文件**完整保留**源文件的所有内容（包含隐藏列、格式、合并单元格等），仅在最右侧追加新列
- 新列表头为 `Duplicate`，值为 `True`（在 folder_a 中存在重复）或 `False`（不存在重复）
- 若输出文件已存在，会被覆盖

## 对比逻辑

### 读取范围

只读取每个文件中名为 **`Detail_1`** 的 sheet。若某文件无此 sheet，程序报错退出。

### 提取 Key 的列（按表头定位）

| 列   | 表头             | 说明                               |
|------|------------------|------------------------------------|
| B    | Scaned Object    | 文件路径（Linux / Windows）        |
| R    | Match Content    | 匹配内容                           |
| S    | Match Context   | 匹配上下文                         |

三个字段均参与对比，区分大小写，严格逐字符匹配。

### 处理流程

1. **遍历 folder_a** 中所有 `.xlsx`（不含子目录），从每个文件的 `Detail_1` sheet 读取上述三列。
2. **B 列路径处理**：提取文件名（去除目录前缀）。Linux 路径用 `/` 分割取最后一段，Windows 路径用 `\` 分割取最后一段。
3. 将 **文件名、Match Content、Match Context** 三个值用不可见分隔符拼接为一个 key，存入 `set`（哈希集合），实现 O(1) 查找。
4. **遍历 folder_b** 中所有 `.xlsx`，同样方式为每一行生成 key。
5. 若 key 存在于 folder_a 的 set 中，标记 `True`；否则标记 `False`。
6. 在原表最后新增 `Duplicate` 列，写入结果，保存到 folder_c。

### 合并单元格处理

B 列（Scaned Object）可能包含合并单元格。`openpyxl` 读取合并单元格时，除左上角单元格有值外，其余合并区域的单元格值为 `None`。

处理策略：向前填充（forward fill）——若当前行 B 列为空，则使用上方最近非空行的 B 列值。这样可以正确还原合并单元格的内容。

> 假设：不存在真正意义上的空值——合并区域之外不应出现 B 列为空的情况。如有，向前填充也会错误地将不相关的上一行值赋给它，但目前按此假设处理。

## 依赖

- Python 3.x
- `openpyxl`（读写 `.xlsx`）

安装：

```bash
pip install openpyxl
```

## 使用方式

```bash
python excel_diff.py <folder_a> <folder_b>
```

示例：

```bash
python excel_diff.py D:\data\baseline D:\data\newscan
```

此时若 `folder_b` 名为 `newscan`，则输出到 `D:\data\newscan_marked`。

## 编码说明

- `.xlsx` 文件本质是 ZIP 压缩包，内部 XML 统一采用 UTF-8 编码。使用 `openpyxl` 库读写不会产生字符集相关的编码错误
- 中文、代码中的特殊符号（`\`、`$`、`\n`、Unicode 等）均以原始字节形式存储，对比时严格逐字符匹配，不做任何转义或规范化
- 不使用 `pandas` / `xlrd` 等可能引入额外编码推断的库

## 注意事项

- 程序**不扫描子目录**，只处理指定文件夹根目录下的 `.xlsx` 文件
- 区分大小写：`FileA.txt` 与 `filea.txt` 视为不同文件
- 输出文件完整保留源文件所有内容（格式、隐藏列、合并单元格等）
