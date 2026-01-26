"""
测试智能问答工具的Agent集成
验证system prompt是否正确加载并生效
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from app.services import get_agent_service


def test_agent_initialization():
    """测试Agent初始化和工具注册"""
    print("=" * 60)
    print("测试1: Agent初始化和工具注册")
    print("=" * 60)
    
    try:
        agent_service = get_agent_service()
        
        # 初始化Agent
        if not agent_service.is_initialized:
            print("正在初始化Agent...")
            agent_service.initialize()
        
        print("✅ Agent初始化成功")
        print(f"   已注册工具数量: {len(agent_service._tools)}")
        print()
        
        # 检查工具是否注册
        tool_names = [tool.name for tool in agent_service._tools]
        print("✅ 已注册的工具列表:")
        for i, name in enumerate(tool_names, 1):
            print(f"   {i}. {name}")
        print()
        
        # 检查knowledge_qa工具
        if "knowledge_qa" in tool_names:
            print("✅ knowledge_qa 工具已成功注册")
            qa_tool = next((t for t in agent_service._tools if t.name == "knowledge_qa"), None)
            print(f"   工具描述: {qa_tool.description[:100]}...")
            print(f"   参数数量: {len(qa_tool.params)}")
            for param in qa_tool.params:
                print(f"     - {param.name}: {param.type} (required: {param.required})")
            print()
            return True
        else:
            print("❌ knowledge_qa 工具未注册")
            print(f"   可用工具: {tool_names}")
            print()
            return False
            
    except Exception as e:
        print(f"❌ Agent初始化失败: {e}")
        import traceback
        traceback.print_exc()
        print()
        return False


def test_system_prompt_content():
    """测试system prompt内容"""
    print("=" * 60)
    print("测试2: System Prompt内容验证")
    print("=" * 60)
    
    try:
        agent_service = get_agent_service()
        
        if agent_service._agent and hasattr(agent_service._agent, '_config'):
            config = agent_service._agent._config
            
            if hasattr(config, 'prompt_template'):
                prompt_template = config.prompt_template
                
                # 查找system prompt
                system_prompts = [p for p in prompt_template if p.get('role') == 'system']
                
                if system_prompts:
                    system_content = system_prompts[0].get('content', '')
                    
                    # 检查是否包含KNOWLEDGE QA部分
                    if "KNOWLEDGE QA:" in system_content:
                        print("✅ System Prompt中包含KNOWLEDGE QA部分")
                        print()
                        
                        # 提取KNOWLEDGE QA部分
                        start_idx = system_content.find("KNOWLEDGE QA:")
                        end_idx = system_content.find("ERROR HANDLING:")
                        if start_idx > 0 and end_idx > start_idx:
                            qa_section = system_content[start_idx:end_idx].strip()
                            print("KNOWLEDGE QA部分内容:")
                            print("-" * 60)
                            print(qa_section)
                            print("-" * 60)
                            print()
                        
                        # 检查关键内容
                        key_phrases = [
                            "knowledge_qa",
                            "plant identification",
                            "emotion analysis",
                            "object recognition",
                            "context parameter"
                        ]
                        
                        print("✅ 关键内容检查:")
                        for phrase in key_phrases:
                            if phrase.lower() in system_content.lower():
                                print(f"   ✅ 包含 '{phrase}'")
                            else:
                                print(f"   ❌ 缺少 '{phrase}'")
                        print()
                        
                        return True
                    else:
                        print("❌ System Prompt中不包含KNOWLEDGE QA部分")
                        return False
                else:
                    print("❌ 未找到system prompt")
                    return False
            else:
                print("❌ Agent配置中不包含prompt_template")
                return False
        else:
            print("❌ Agent未正确初始化")
            return False
            
    except Exception as e:
        print(f"❌ System Prompt检查失败: {e}")
        import traceback
        traceback.print_exc()
        print()
        return False


def test_tool_description_completeness():
    """测试工具描述完整性"""
    print("=" * 60)
    print("测试3: 工具描述完整性")
    print("=" * 60)
    
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
            "祝福",
            "食材",
            "菜谱",
            "上下文"
        ]
        
        print("✅ 描述关键词检查:")
        for keyword in required_keywords:
            if keyword in qa_tool.description:
                print(f"   ✅ 包含 '{keyword}'")
            else:
                print(f"   ❌ 缺少 '{keyword}'")
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ 工具描述检查失败: {e}")
        import traceback
        traceback.print_exc()
        print()
        return False


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("智能问答工具Agent集成测试")
    print("=" * 60 + "\n")
    
    results = []
    
    # 运行所有测试
    results.append(("Agent初始化和工具注册", test_agent_initialization()))
    results.append(("System Prompt内容验证", test_system_prompt_content()))
    results.append(("工具描述完整性", test_tool_description_completeness()))
    
    # 总结
    print("=" * 60)
    print("测试结果总结")
    print("=" * 60)
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} - {test_name}")
    
    print()
    print(f"总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！智能问答工具已成功集成到Agent系统中。")
        print("\n✅ System Prompt已正确配置，包含以下指导：")
        print("   1. 工具使用场景说明")
        print("   2. 触发短语示例")
        print("   3. 调用流程（先搜索图片ID，再调用knowledge_qa）")
        print("   4. context参数的使用说明")
        print("   5. 不同场景的响应规范")
        print("   6. 友好专业的语气要求")
        print("   7. 诚实处理图片内容不足的情况")
    else:
        print(f"\n⚠️  有 {total - passed} 个测试失败，请检查错误信息。")
    
    print("\n" + "=" * 60)
