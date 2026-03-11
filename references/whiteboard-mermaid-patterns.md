# Whiteboard Mermaid Patterns

Use compact, readable layouts. Prefer `TB` and grouped subgraphs when node count grows.

## 1. Main Flow + Local Branch

```mermaid
flowchart TB
  A[入口] --> B[阶段一]
  B --> C[阶段二]
  C --> D[阶段三]

  subgraph BR[分支处理]
    X[条件判断] --> Y[分支动作]
    Y --> Z[回到主线]
  end

  C --> X
  Z --> D
```

## 2. Two-Layer Pipeline

```mermaid
flowchart TB
  subgraph L1[准备层]
    A1[输入检查] --> A2[上下文初始化]
  end

  subgraph L2[执行层]
    B1[主流程执行] --> B2[结果汇总]
  end

  A2 --> B1
```

## 3. Line Break Rule

In Feishu whiteboard Mermaid labels, use `<br/>` instead of `\n`.

Example:

```mermaid
flowchart TB
  A[阶段一<br/>参数准备] --> B[阶段二<br/>执行与回调]
```

## 4. Whiteboard Revision Procedure

1. Delete old whiteboard block.
2. Create a new whiteboard block at the same index.
3. Fill the new whiteboard once.
4. Verify block structure and confirm only the new whiteboard remains.
