     继Anthropic后，Google放出5个常用的Agent Skill设计模式 \* { margin: 0; padding: 0; outline: 0; } body { font-family: "PingFang SC", system-ui, -apple-system, BlinkMacSystemFont, "Helvetica Neue", "Hiragino Sans GB", "Microsoft YaHei UI", "Microsoft YaHei", Arial, sans-serif; line-height: 1.6; } .\_\_page\_content\_\_ { max-width: 667px; margin: 0 auto; padding: 20px; text-size-adjust: 100%; color: rgba(0, 0, 0, 0.9); padding-bottom: 64px; } .title { user-select: text; font-size: 22px; line-height: 1.4; margin-bottom: 14px; font-weight: 500; } .\_\_meta\_\_ { color: rgba(0, 0, 0, 0.3); font-size: 15px; line-height: 20px; hyphens: auto; word-break: break-word; margin-bottom: 50px; } .\_\_meta\_\_ .nick\_name { color: #576B95; } .\_\_meta\_\_ .copyright { color: rgba(0, 0, 0, 0.3); background-color: rgba(0, 0, 0, 0.05); padding: 0 4px; margin: 0 10px 10px 0; } blockquote.source { padding: 10px; margin: 30px 0; border-left: 5px solid #ccc; color: #333; font-style: italic; word-wrap: break-word; } blockquote.source a { cursor: pointer; text-decoration: underline; } .item\_show\_type\_0 > section { margin-top: 0; margin-bottom: 24px; } a { color: #576B95; text-decoration: none; cursor: default; } .text\_content { margin-bottom: 50px; user-select: text; font-size: 17px; white-space: pre-wrap; word-wrap: break-word; line-height: 28px; hyphens: auto; } .picture\_content .picture\_item { margin-bottom: 30px; } .picture\_content .picture\_item .picture\_item\_label { text-align: center; } img { max-width: 100%; } .\_\_bottom-bar\_\_ { display: flex; justify-content: space-between; align-items: center; position: fixed; bottom: 0; left: 0; right: 0; height: 64px; padding: 8px 20px; background: white; box-sizing: border-box; border-top: 1px solid rgba(0, 0, 0, 0.2); } .\_\_bottom-bar\_\_ .left { display: flex; align-items: center; font-size: 15px; white-space: nowrap; } .\_\_bottom-bar\_\_ .right { display: flex; } .\_\_bottom-bar\_\_ .sns\_opr\_btn { display: flex; align-items: center; user-select: none; background: transparent; border: 0; color: rgba(0, 0, 0, 0.9); font-size: 14px; } .\_\_bottom-bar\_\_ .sns\_opr\_btn:not(:last-child) { margin-right: 16px; } .\_\_bottom-bar\_\_ .sns\_opr\_btn > img { margin-right: 4px; }

继Anthropic后，Google放出5个常用的Agent Skill设计模式
========================================

原创 winkrun AI工程化 2026-03-19 06:12 北京

> 原文地址: [https://mp.weixin.qq.com/s/yu120tW0l4DJAJfWmbJYxg](https://mp.weixin.qq.com/s/yu120tW0l4DJAJfWmbJYxg)

如果你也在写Agent Skills，应该会发现一个尴尬的事实：SKILL.md的格式已经标准化了，三十多个主流工具（Claude Code、Gemini CLI、Cursor……）都支持同一种写法。格式不再是问题，但很多人写着写着就发现——同样格式的skill，执行效果天差地别。

问题出在内容设计上。同样是一个skill，包装FastAPI规范和实现一个四步文档流水线，内部的逻辑结构完全不同，但外在看起来一模一样。Google Cloud最新发布的这份指南，由Saboo\_Shubham\_和lavinigam撰写，就是专门解决这个问题的。

这份指南总结了五种经过验证的设计模式，每种都有完整的ADK代码示例。

![](https://mmbiz.qpic.cn/sz_mmbiz_jpg/rY5icXvTTrJic2qIkBBHvwGnLWxpYnnJz9icAQfZWbBQFecXcRSkCaGYzZrtChZaQ6lonxZ5ZSMUbPq0qojFsroIqrID5upE4uTXFwNM53libgA/640?wx_fmt=jpeg)

Tool Wrapper：让agent快速成为某个领域的专家
------------------------------

这是最容易上手的模式。简单说，就是把某个库或框架的规范文档打包成一个skill，agent只有在真正用到这个技术时才会加载相关文档。

比如一个写FastAPI的skill，不需要把所有的API约定都塞进system prompt，而是让SKILL.md监听特定的库关键词，当用户开始写FastAPI代码时才动态加载references/目录下的conventions.md，把这些规则当作绝对真理来执行。

![](https://mmbiz.qpic.cn/sz_mmbiz_jpg/rY5icXvTTrJicPKib3Gk3NSkVQmMdIIodbTW92MAo5T6v05UhVBibQkdno0JwibYYD1saO2YlqbIuTUJ7TRJQw9yiaJ4Z3NibXXRNuia4ic8S67KwSjk/640?wx_fmt=jpeg)

这特别适合分发团队内部的编码规范或者特定框架的最佳实践。

Generator：从模板生成结构化输出
--------------------

如果Tool Wrapper是应用知识，Generator则是强制一致的输出格式。很多agent每次运行生成的文档结构都不一样，Generator通过一个“填空”流程解决这个问题。

它利用两个可选目录：assets/存放输出模板，references/存放样式指南。SKILL.md扮演项目经理的角色，指示agent加载模板、读取样式指南、向用户询问缺失的变量、然后填充文档。

![](https://mmbiz.qpic.cn/mmbiz_jpg/rY5icXvTTrJic8icxFxDNsUYgIkQ513HmKBHTicF8yaehPRNu6GeJI9BP60XogCmiabLkOpvD7sdBFc7ssv4yJsz0MGFtm4Qic1a8HVlaLIuqaozY/640?wx_fmt=jpeg)

这对于生成统一的API文档、标准化commit信息或者脚手架项目结构都非常实用。

Reviewer：把检查清单和检查逻辑分开
---------------------

非常实用的模式之一。传统的代码审查会把所有规则都写进system prompt，结果越写越长。Reviewer模式把“检查什么”和“怎么检查”完全分开。

审查标准存放在references/review-checklist.md里，可以是Python风格检查，也可以换成OWASP安全检查——同样的skill基础设施，换个清单就是完全不同的专项审计。

![](https://mmbiz.qpic.cn/sz_mmbiz_jpg/rY5icXvTTrJibMUFnk3NA1AE9l9e2kS0Ebjuh3RSlN7dibqQRia1XD1c2gqkvibUqeNrAOSjByeww0rFCpIDvq5sYKVO5JgK7WxFzCUzN5VhfPs8/640?wx_fmt=jpeg)

代码示例展示了一个Python代码审查skill的结构。指令保持静态，但agent会动态加载特定的审查标准，并强制输出按严重程度分组的结构化结果。  

Inversion：agent先问你再做
--------------------

这是最反直觉的模式。Agent天生喜欢直接猜测和生成，Inversion把这个流程完全反过来——agent变成面试官，先问你一系列问题，等你回答完再行动。

关键在于明确、不可协商的门控指令（比如“不到所有阶段完成就不开始构建”）。Agent会逐个阶段提问，等待你的答案，然后才进入下一个阶段。

![](https://mmbiz.qpic.cn/mmbiz_jpg/rY5icXvTTrJicFUPXsGY5iaUkTg3ruMpblzO8HH8G7qVicQ1MtgcssqLn5tMC1E7h3u9POpms3gRNdKwTD6AGd92UEl8YcZ33ibT9UPWkibxrXvfM/640?wx_fmt=jpeg)

一个项目规划skill的示例展示了这一点：必须等用户回答完所有问题，agent才会加载plan-template.md并生成最终计划。  

Pipeline：带硬性检查点的严格工作流
---------------------

对于复杂任务，你承受不起跳过步骤或者忽略指令的情况。Pipeline模式强制执行严格的顺序工作流，并在关键节点设置硬性检查点。

指令本身定义了工作流。通过实现明确的门控条件（比如要求用户在进入下一步之前确认生成的文档字符串），Pipeline确保agent无法绕过复杂任务直接给出未验证的最终结果。

![](https://mmbiz.qpic.cn/sz_mmbiz_jpg/rY5icXvTTrJ8eDopEOQagfb2ly4SLcEAfpOuB3cEvUftkBicyFd26NwRwLgFPPOnVliculyuYYB8oyrKCHcZ3PlyyVbnUduBUFtle2ylF1Cwko/640?wx_fmt=jpeg)

一个文档流水线的例子展示了四个步骤：解析和清点、生成文档字符串、组装文档、质量检查。每一步都有明确的前置条件，用户必须在进入下一步之前确认。

选择合适的模式

每个模型都有其应用场景，可以根据下图来判断使用合适的模式。

![](https://mmbiz.qpic.cn/sz_mmbiz_jpg/rY5icXvTTrJicICq9AtyFicic74SrakllpLiawKd63JhOeIblqyo7UBV1E5iaRkiaex6LWnfZz4iajIHb3IFiaBae3PNkWlPiczfWwVbwbtxQDzVoSH48/640?wx_fmt=jpeg)

这些模式可以组合使用
----------

这是容易被忽视的一点。这五种模式并非互斥，而是可以组合。Pipeline可以在最后包含一个Reviewer步骤来 double-check 自己的成果；Generator可以在最开始依赖Inversion来收集必要的变量。

多亏了ADK的SkillToolset和渐进式披露机制，agent只在运行时需要时才消耗上下文token来加载特定的模式。

别再把所有复杂又脆弱的指令塞进一个system prompt了。把工作流拆分开，应用正确的结构模式，才能构建出真正可靠的agent。

有条件的可以去看英文原文，里面有完整的代码示例。

另外，还有anthropic的skill实践，感兴趣可以阅读。

![](https://mmbiz.qpic.cn/mmbiz_jpg/rY5icXvTTrJibg6xVQjjtibfpBxvPTNhpSes3GO8IDCEL59NV8JZSrmeMU6B2lyYibkOiaLYbblHWsicUmDqHxibDvxGNlqRNcZIPKAkCIOXlWqb3Y/640?wx_fmt=jpeg)

> Anthropic 把内部几百个 Skills 用了个遍，发现最好的 Skill 不是写得好的提示词，而是一个「工具箱」。他们把 Skills 分成九类，从参考手册到故障排查，每类都有明确的场景。写好 Skill 的三条铁律：只写 Agent 不知道的东西、重点写踩坑清单、给工具不给指令。
> 
> Anthropic工程师分享的Claude Code技能设计指南：9种类型与实战技巧 https://wink.run/pings/content/111668?from=wx

相关链接：

*   原文：https://x.com/i/article/2033941492633362432
    
*   awesome-agent-skills：https://github.com/skillmatic-ai/awesome-agent-skills
    

关注公众号回复“进群”入群讨论。

![](http://mmbiz.qpic.cn/mmbiz_png/aaN2xdFqa4HHZgg9abQ55cSWZu23JrNMHD5SBdsYLURCtEcAfhyxNzG4boYKKWTUibhOx8wbupSOzFD1Dd0PFzw/0?wx_fmt=png) AI工程化

 ![](data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24'%3E%3C!-- Icon from Lucide by Lucide Contributors - https://github.com/lucide-icons/lucide/blob/main/LICENSE --%3E%3Cg fill='none' stroke='%23888888' stroke-linecap='round' stroke-linejoin='round' stroke-width='2'%3E%3Cpath d='M2.062 12.348a1 1 0 0 1 0-.696a10.75 10.75 0 0 1 19.876 0a1 1 0 0 1 0 .696a10.75 10.75 0 0 1-19.876 0'/%3E%3Ccircle cx='12' cy='12' r='3'/%3E%3C/g%3E%3C/svg%3E) 阅读![](data:image/svg+xml,%3Csvg width='25' height='24' viewBox='0 0 25 24' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath fill-rule='evenodd' clip-rule='evenodd' d='M16.154 6.797l-.177 2.758h4.009c1.346 0 2.359 1.385 2.155 2.763l-.026.148-1.429 6.743c-.212.993-1.02 1.713-1.977 1.783l-.152.006-13.707-.006c-.553 0-1-.448-1-1v-8.58a1 1 0 0 1 1-1h2.44l1.263-.03.417-.018.168-.015.028-.005c1.355-.315 2.39-2.406 2.58-4.276l.01-.16.022-.572.022-.276c.074-.707.3-1.54 1.08-1.883 2.054-.9 3.387 1.835 3.274 3.62zm-2.791-2.52c-.16.07-.282.294-.345.713l-.022.167-.019.224-.023.604-.014.204c-.253 2.486-1.615 4.885-3.502 5.324l-.097.018-.204.023-.181.012-.256.01v8.218l9.813.004.11-.003c.381-.028.72-.304.855-.709l.034-.125 1.422-6.708.02-.11c.099-.668-.354-1.308-.87-1.381l-.098-.007h-5.289l.26-4.033c.09-1.449-.864-2.766-1.594-2.446zM7.5 11.606l-.21.005-2.241-.001v8.181l2.45.001v-8.186z' fill='%23000'/%3E%3C/svg%3E) 赞 ![](data:image/svg+xml;charset=utf8,%3Csvg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24'%3E  %3Cg fill='none' fill-rule='evenodd'%3E    %3Cpath d='M0 0h24v24H0z'/%3E    %3Cpath fill='%23576B95' d='M13.707 3.288l7.171 7.103a1 1 0 0 1 .09 1.32l-.09.1-7.17 7.104a1 1 0 0 1-1.705-.71v-3.283c-2.338.188-5.752 1.57-7.527 5.9-.295.72-1.02.713-1.177-.22-1.246-7.38 2.952-12.387 8.704-13.294v-3.31a1 1 0 0 1 1.704-.71zm-.504 5.046l-1.013.16c-4.825.76-7.976 4.52-7.907 9.759l.007.287c1.594-2.613 4.268-4.45 7.332-4.787l1.581-.132v4.103l6.688-6.623-6.688-6.623v3.856z'/%3E  %3C/g%3E%3C/svg%3E) 分享 ![](data:image/svg+xml;charset=utf8,%3Csvg xmlns='http://www.w3.org/2000/svg' xmlns:xlink='http://www.w3.org/1999/xlink' width='24' height='24' viewBox='0 0 24 24'%3E  %3Cdefs%3E    %3Cpath id='a62bde5b-af55-42c8-87f2-e10e8a48baa0-a' d='M0 0h24v24H0z'/%3E  %3C/defs%3E  %3Cg fill='none' fill-rule='evenodd'%3E    %3Cmask id='a62bde5b-af55-42c8-87f2-e10e8a48baa0-b' fill='%23fff'%3E      %3Cuse xlink:href='%23a62bde5b-af55-42c8-87f2-e10e8a48baa0-a'/%3E    %3C/mask%3E    %3Cg mask='url(%23a62bde5b-af55-42c8-87f2-e10e8a48baa0-b)'%3E      %3Cg transform='translate(0 -2.349)'%3E        %3Cpath d='M0 2.349h24v24H0z'/%3E        %3Cpath fill='%23576B95' d='M16.45 7.68c-.954 0-1.94.362-2.77 1.113l-1.676 1.676-1.853-1.838a3.787 3.787 0 0 0-2.63-.971 3.785 3.785 0 0 0-2.596 1.112 3.786 3.786 0 0 0-1.113 2.687c0 .97.368 1.938 1.105 2.679l7.082 6.527 7.226-6.678a3.787 3.787 0 0 0 .962-2.618 3.785 3.785 0 0 0-1.112-2.597A3.687 3.687 0 0 0 16.45 7.68zm3.473.243a4.985 4.985 0 0 1 1.464 3.418 4.98 4.98 0 0 1-1.29 3.47l-.017.02-7.47 6.903a.9.9 0 0 1-1.22 0l-7.305-6.73-.008-.01a4.986 4.986 0 0 1-1.465-3.535c0-1.279.488-2.56 1.465-3.536A4.985 4.985 0 0 1 7.494 6.46c1.24-.029 2.49.4 3.472 1.29l.01.01L12 8.774l.851-.85.01-.01c1.046-.951 2.322-1.434 3.59-1.434 1.273 0 2.52.49 3.472 1.442z'/%3E      %3C/g%3E    %3C/g%3E  %3C/g%3E%3C/svg%3E) 推荐 ![](data:image/svg+xml,%3Csvg width='25' height='24' viewBox='0 0 25 24' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M22.242 7a2.5 2.5 0 0 0-2.5-2.5h-14a2.5 2.5 0 0 0-2.5 2.5v8.5a2.5 2.5 0 0 0 2.5 2.5h2.5v1.59a1 1 0 0 0 1.707.7l1-1a.569.569 0 0 0 .034-.03l1.273-1.273a.6.6 0 0 0-.8-.892v-.006L9.441 19.1l.001-2.3h-3.7l-.133-.007A1.3 1.3 0 0 1 4.442 15.5V7l.007-.133A1.3 1.3 0 0 1 5.742 5.7h14l.133.007A1.3 1.3 0 0 1 21.042 7v4.887a.6.6 0 1 0 1.2 0V7z' fill='%23000' fill-opacity='.9'/%3E%3Crect x='14.625' y='16.686' width='7' height='1.2' rx='.6' fill='%23000' fill-opacity='.9'/%3E%3Crect x='18.725' y='13.786' width='7' height='1.2' rx='.6' transform='rotate(90 18.725 13.786)' fill='%23000' fill-opacity='.9'/%3E%3C/svg%3E) 留言