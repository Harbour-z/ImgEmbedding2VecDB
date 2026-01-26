import React from 'react';
import { Typography } from 'antd';
import { MarkdownRenderer } from '../components/common/MarkdownRenderer';

const { Title } = Typography;

const testMarkdown = `
# Markdown渲染测试

这是一段测试文本，用于验证Markdown渲染功能。

## 基础语法

### 文本样式

这是**粗体文本**，这是*斜体文本*，这是\`行内代码\`。

### 列表

**无序列表：**
- 第一项
- 第二项
  - 子项1
  - 子项2
- 第三项

**有序列表：**
1. 第一步
2. 第二步
3. 第三步

### 引用

> 这是一段引用文本。
> 可以有多行。

### 链接和图片

[访问Google](https://www.google.com)

### 表格

| 名称 | 年龄 | 职业 |
|------|------|------|
| 张三 | 25 | 工程师 |
| 李四 | 30 | 设计师 |
| 王五 | 28 | 产品经理 |

## 代码高亮测试

### Python代码

\`\`\`python
def hello_world():
    """
    打印Hello World
    """
    print("Hello, World!")
    return True

class Calculator:
    def add(self, a, b):
        return a + b
    
    def multiply(self, a, b):
        return a * b
\`\`\`

### JavaScript代码

\`\`\`javascript
// 这是一个JavaScript函数
function calculateSum(arr) {
    return arr.reduce((acc, curr) => acc + curr, 0);
}

const numbers = [1, 2, 3, 4, 5];
const sum = calculateSum(numbers);
console.log('Sum:', sum);
\`\`\`

### CSS代码

\`\`\`css
.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
    background-color: #f5f5f5;
}

.button {
    padding: 10px 20px;
    border: none;
    border-radius: 5px;
    background-color: #1890ff;
    color: white;
    cursor: pointer;
}
\`\`\`

### JSON代码

\`\`\`json
{
    "name": "测试用户",
    "age": 25,
    "skills": [
        "Python",
        "JavaScript",
        "TypeScript"
    ],
    "active": true
}
\`\`\`

## 复杂示例

### 混合使用

这里有一段**重要**的文字，包含\`行内代码\`和一个[链接](https://example.com)。

> 💡 提示：代码块会自动进行语法高亮！

### 多级标题

#### 第四级标题

一些内容...

##### 第五级标题

更多内容...

###### 第六级标题

最小级别标题。

### 水平线

---

上面的内容是标题和段落。

---

下面是代码示例。
`;

export const MarkdownTestPage: React.FC = () => {
  return (
    <div style={{ padding: '24px', maxWidth: 900, margin: '0 auto' }}>
      <Title level={2} style={{ marginBottom: 24 }}>
        Markdown渲染功能测试
      </Title>
      
      <div style={{
        border: '1px solid #d9d9d9',
        borderRadius: '8px',
        padding: '24px',
        backgroundColor: '#fff'
      }}>
        <MarkdownRenderer content={testMarkdown} />
      </div>
    </div>
  );
};
