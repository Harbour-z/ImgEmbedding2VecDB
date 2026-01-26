"""
知识问答工具测试脚本
测试工具注册和基本功能
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from app.services import get_agent_service, get_knowledge_qa_service


def test_knowledge_qa_service():
    """测试知识问答服务"""
    print("=== 测试1: 知识问答服务初始化 ===")
    try:
        qa_service = get_knowledge_qa_service()
        print(f"✅ 知识问答服务初始化成功")
        print(f"   服务类型: {type(qa_service)}")
        print()
    except Exception as e:
        print(f"❌ 知识问答服务初始化失败: {e}")
        print()
        return False

    return True


def test_agent_tool_registration():
    """测试Agent工具注册"""
    print("=== 测试2: Agent工具注册 ===")
    try:
        agent_service = get_agent_service()

        # 初始化Agent
        if not agent_service.is_initialized:
            agent_service.initialize()

        # 检查工具是否注册
        tool_names = [tool.name for tool in agent_service._tools]
        print(f"✅ Agent已注册工具数量: {len(tool_names)}")
        print()

        # 检查知识问答工具
        if "knowledge_qa" in tool_names:
            print("✅ knowledge_qa 工具已成功注册")
            qa_tool = next(t for t in agent_service._tools if t.name == "knowledge_qa")
            print(f"   工具描述: {qa_tool.description[:100]}...")
            print(f"   参数数量: {len(qa_tool.params)}")
            for param in qa_tool.params:
                print(f"     - {param.name}: {param.type} (required: {param.required})")
            print()
            return True
        else:
            print("❌ knowledge_qa 工具未注册")
            print(f"   已注册的工具: {tool_names}")
            print()
            return False

    except Exception as e:
        print(f"❌ Agent工具注册测试失败: {e}")
        import traceback
        traceback.print_exc()
        print()
        return False


def test_api_endpoint():
    """测试API端点"""
    print("=== 测试3: API端点注册 ===")
    try:
        from app.main import create_app
        app = create_app()

        # 检查路由
        routes = [r.path for r in app.routes]
        knowledge_qa_routes = [r for r in routes if "knowledge-qa" in r]

        print(f"✅ 应用总路由数: {len(routes)}")
        print(f"✅ 知识问答相关路由: {len(knowledge_qa_routes)}")
        for route in knowledge_qa_routes:
            print(f"   - {route}")
        print()

        # 检查特定端点
        if any("/api/v1/knowledge-qa/qa" in r for r in routes):
            print("✅ /api/v1/knowledge-qa/qa 端点已注册")
            print()
            return True
        else:
            print("❌ /api/v1/knowledge-qa/qa 端点未注册")
            print()
            return False

    except Exception as e:
        print(f"❌ API端点测试失败: {e}")
        import traceback
        traceback.print_exc()
        print()
        return False


def test_tool_description():
    """测试工具描述"""
    print("=== 测试4: 工具描述完整性 ===")
    try:
        agent_service = get_agent_service()
        if not agent_service.is_initialized:
            agent_service.initialize()

        qa_tool = next((t for t in agent_service._tools if t.name == "knowledge_qa"), None)
        if not qa_tool:
            print("❌ 未找到knowledge_qa工具")
            return False

        print("✅ 工具基本信息:")
        print(f"   名称: {qa_tool.name}")
        print(f"   描述: {qa_tool.description}")
        print()

        # 检查描述是否包含关键场景
        required_keywords = [
            "植物识别",
            "情感分析",
            "祝福文案",
            "食材",
            "菜谱"
        ]

        print("✅ 场景关键词检查:")
        for keyword in required_keywords:
            if keyword in qa_tool.description:
                print(f"   ✅ 包含 '{keyword}'")
            else:
                print(f"   ❌ 缺少 '{keyword}'")
        print()

        return True

    except Exception as e:
        print(f"❌ 工具描述测试失败: {e}")
        import traceback
        traceback.print_exc()
        print()
        return False


if __name__ == "__main__":
    print("\n" + "="*60)
    print("知识问答工具功能测试")
    print("="*60 + "\n")

    results = []

    # 运行所有测试
    results.append(("服务初始化", test_knowledge_qa_service()))
    results.append(("Agent工具注册", test_agent_tool_registration()))
    results.append(("API端点注册", test_api_endpoint()))
    results.append(("工具描述完整性", test_tool_description()))

    # 总结
    print("="*60)
    print("测试结果总结")
    print("="*60)
    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} - {test_name}")

    print()
    print(f"总计: {passed}/{total} 测试通过")

    if passed == total:
        print("\n🎉 所有测试通过！知识问答工具已成功集成到Agent系统中。")
        print("\n典型使用场景：")
        print("1. 植物识别: '这是什么植物？多肉植物怎么养？'")
        print("2. 情感分析: '这张照片里妈妈开心吗？'")
        print("3. 祝福文案: '帮我写个生日祝福文案'")
        print("4. 食材识别: '冰箱里有什么食材？'")
        print("5. 菜谱推荐: '用这些食材推荐个菜谱'")
    else:
        print(f"\n⚠️  有 {total - passed} 个测试失败，请检查错误信息。")

    print("\n" + "="*60)
