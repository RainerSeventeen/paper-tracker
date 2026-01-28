# arXiv API: `search_query` 字段与语法说明

本文档总结 arXiv Atom API（`/api/query`）中 `search_query` 参数支持的常用字段与写法，并给出与本项目配置的对应关系。

> 说明：这里的“字段(field)”指 `search_query` 里的前缀（如 `cat:`、`ti:`），不是 HTTP 参数名。

---

## 1. arXiv Atom API 请求参数概览

arXiv Atom API 的典型请求形如：

```text
https://export.arxiv.org/api/query?search_query=<QUERY>&start=0&max_results=20&sortBy=submittedDate&sortOrder=descending
```

常用参数：

- `search_query`: 搜索表达式（本文重点）
- `id_list`: 以逗号分隔的 arXiv id 列表（与 `search_query` 二选一使用）
- `start`: 结果起始偏移
- `max_results`: 返回条数
- `sortBy`: 常见为 `submittedDate` / `lastUpdatedDate`
- `sortOrder`: `ascending` / `descending`

本项目目前只使用 `search_query` + `start/max_results/sortBy/sortOrder`。

---

## 2. `search_query` 的字段（Field Prefix）

`search_query` 使用 `field:value` 的形式进行限定搜索。以下是常见字段：

### 2.1 `cat:`（Category）

- 作用：按 arXiv 分类过滤
- 例子：
  - `cat:cs.CV`
  - `cat:cs.LG`
  - `(cat:cs.CV OR cat:cs.LG)`

详细参见 [arxiv 官方说明](https://arxiv.org/category_taxonomy)

`cs.CV` 这类值是 arXiv 分类代码（`<major>.<minor>`）。

### 2.2 `ti:`（Title）

- 作用：仅在标题中搜索
- 例子：
  - `ti:diffusion`
  - `ti:"large language model"`

### 2.3 `abs:`（Abstract）

- 作用：仅在摘要中搜索
- 例子：
  - `abs:transformer`

### 2.4 `au:`（Author）

- 作用：按作者名搜索
- 例子：
  - `au:"Yann LeCun"`
  - `au:LeCun`

### 2.5 `co:`（Comments）

- 作用：在 comments 字段中搜索（不少论文会在此写会议/期刊信息）
- 例子：
  - `co:ICCV`
  - `co:"NeurIPS 2024"`

### 2.6 `jr:`（Journal Reference）

- 作用：在 journal reference 字段中搜索
- 例子：
  - `jr:"Nature"`

### 2.7 `all:`（All Fields）

- 作用：在 arXiv 提供的“全字段”中搜索（范围通常比 `ti/abs` 更广）
- 例子：
  - `all:diffusion`

### 2.8 `id:`（Identifier）

- 作用：按 arXiv identifier 搜索（与 `id_list` 的用途相关）
- 例子：
  - `id:1234.5678`

---

## 3. `search_query` 的布尔语法（AND / OR / NOT）

arXiv 的查询字符串支持布尔组合与括号分组，常见写法：

- `AND`：
  - `cat:cs.CV AND ti:diffusion`
- `OR`：
  - `cat:cs.CV OR cat:cs.LG`
- `NOT` / `AND NOT`：
  - `cat:cs.CV AND NOT ti:survey`
- 括号分组：
  - `(cat:cs.CV OR cat:cs.LG) AND (ti:diffusion OR abs:diffusion)`

短语（包含空格）通常需要用双引号包裹：

- `ti:"large language model"`

---

## 4. 与本项目配置的对应关系

本项目的配置文件中使用结构化 query（`queries` 列表），而不是直接让用户手写 arXiv 的 `search_query`。

配置层使用语义字段：

- `TITLE` / `ABSTRACT` / `AUTHOR` / `JOURNAL` / `CATEGORY`
- 也支持不写字段，直接在 query 顶层写 `AND`/`OR`/`NOT`（等价于 `TEXT`：标题+摘要）

每个字段下支持三个操作符键（要求大写）：

- `AND`: 必须同时满足（列表）
- `OR`: 任一满足即可（列表）
- `NOT`: 排除（列表）

本项目会将这些结构编译成 arXiv Atom API 的 `search_query`。

```yml
queries:
  - NAME: example
    CATEGORY:
      OR: [cs.CV]
    TITLE:
      OR: [diffusion]
      NOT: [survey]
```

规则：

- 本项目会把每条 query 编译为 arXiv 的 `search_query` 再发送。

---

## 5. 示例

### 5.1 只写 value（由项目自动扩展字段）

```text
diffusion AND "large language model"
```

### 5.2 明确指定分类 + 标题

```text
cat:cs.CV AND ti:diffusion AND NOT all:survey
```

### 5.3 多分类 + 多关键词

```text
(cat:cs.CV OR cat:cs.LG) AND (diffusion OR transformer) AND NOT all:survey
```

---

## 6. 常见注意事项

- 多词不加引号会被当成多个 term：`large language model` 等价于 `large AND language AND model`（本项目支持隐式 AND）。
- 建议在 YAML 里把整个表达式用单引号包起来，以便表达式内部使用双引号短语。
