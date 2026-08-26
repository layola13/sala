var TOC = [
 {
  "t": "入门指南",
  "f": null,
  "c": [
   {
    "t": "SA 与 SLA 概述",
    "f": "content/01_overview/01_sa_sla_overview.html",
    "c": []
   },
   {
    "t": "安装与构建",
    "f": "content/01_overview/02_install_build.html",
    "c": []
   },
   {
    "t": "快速上手：第一个 SLA 程序",
    "f": "content/01_overview/03_quick_start.html",
    "c": []
   },
   {
    "t": "工具链组成",
    "f": "content/01_overview/04_toolchain.html",
    "c": []
   },
   {
    "t": "项目与 workspace",
    "f": "content/01_overview/05_projects_workspace.html",
    "c": []
   }
  ]
 },
 {
  "t": "SLA 语言参考",
  "f": null,
  "c": [
   {
    "t": "词法与基础语法",
    "f": "content/02_sla_lang/01_lexical.html",
    "c": []
   },
   {
    "t": "类型系统",
    "f": "content/02_sla_lang/02_types.html",
    "c": []
   },
   {
    "t": "函数与控制流",
    "f": "content/02_sla_lang/03_functions.html",
    "c": []
   },
   {
    "t": "模式匹配",
    "f": "content/02_sla_lang/04_patterns.html",
    "c": []
   },
   {
    "t": "结构体与枚举",
    "f": "content/02_sla_lang/05_structs_enums.html",
    "c": []
   },
   {
    "t": "所有权与生命周期",
    "f": "content/02_sla_lang/06_ownership.html",
    "c": []
   },
   {
    "t": "模块与 @import",
    "f": "content/02_sla_lang/07_modules.html",
    "c": []
   },
   {
    "t": "扩展机制",
    "f": "content/02_sla_lang/08_extensions.html",
    "c": []
   },
   {
    "t": "async/await 现状",
    "f": "content/02_sla_lang/09_async.html",
    "c": []
   },
   {
    "t": "特性成熟度总表",
    "f": "content/02_sla_lang/10_maturity.html",
    "c": []
   }
  ]
 },
 {
  "t": "与 Rust 对比",
  "f": null,
  "c": [
   {
    "t": "定位与设计哲学：SLA 不是 Rust 克隆",
    "f": "content/09_rust_compare/01_positioning.html",
    "c": []
   },
   {
    "t": "语法对照实测矩阵",
    "f": "content/09_rust_compare/02_syntax_matrix.html",
    "c": []
   },
   {
    "t": "所有权与借用：Referee 对比 borrow checker",
    "f": "content/09_rust_compare/03_ownership.html",
    "c": []
   },
   {
    "t": "宏与元编程对比",
    "f": "content/09_rust_compare/04_macros.html",
    "c": []
   },
   {
    "t": "标准库、错误处理与 async 对照",
    "f": "content/09_rust_compare/05_stdlib_errors_async.html",
    "c": []
   },
   {
    "t": "Rust 表层兼容性：哪些代码能原样解析",
    "f": "content/09_rust_compare/06_surface_compat.html",
    "c": []
   },
   {
    "t": "rosetta 对照集与 bc2sa 桥接生态",
    "f": "content/09_rust_compare/07_rosetta_bc2sa.html",
    "c": []
   },
   {
    "t": "从 Rust 迁移到 SLA：改写清单与场景选择",
    "f": "content/09_rust_compare/08_migration.html",
    "c": []
   }
  ]
 },
 {
  "t": "SA 汇编与 SAB",
  "f": null,
  "c": [
   {
    "t": "SA 概念模型",
    "f": "content/03_sa_asm/01_sa_model.html",
    "c": []
   },
   {
    "t": "SA 文本汇编速览",
    "f": "content/03_sa_asm/02_sa_syntax.html",
    "c": []
   },
   {
    "t": "SAB 字节码格式概览",
    "f": "content/03_sa_asm/03_sab_format.html",
    "c": []
   },
   {
    "t": "编译管线：direct 与 fallback",
    "f": "content/03_sa_asm/04_pipeline.html",
    "c": []
   },
   {
    "t": "错误码与诊断",
    "f": "content/03_sa_asm/05_diagnostics.html",
    "c": []
   },
   {
    "t": "已知限制",
    "f": "content/03_sa_asm/06_limitations.html",
    "c": []
   }
  ]
 },
 {
  "t": "命令行参考",
  "f": null,
  "c": [
   {
    "t": "命令行参考总览",
    "f": "content/04_cli/01_overview.html",
    "c": [
     {
      "t": "sa sla init",
      "f": "content/04_cli/02_init.html",
      "c": []
     },
     {
      "t": "sa sla check",
      "f": "content/04_cli/03_check.html",
      "c": []
     },
     {
      "t": "sa sla build",
      "f": "content/04_cli/04_build.html",
      "c": []
     },
     {
      "t": "sa sla build-exe / build-workspace",
      "f": "content/04_cli/05_build_exe.html",
      "c": []
     },
     {
      "t": "sa sla sab（build / workspace / disasm）",
      "f": "content/04_cli/06_sab.html",
      "c": []
     },
     {
      "t": "sa sla test",
      "f": "content/04_cli/07_test.html",
      "c": []
     },
     {
      "t": "sa sla skills 与 stability",
      "f": "content/04_cli/08_skills.html",
      "c": []
     }
    ]
   },
   {
    "t": "宿主侧 sa build-exe / sa test 概览",
    "f": "content/04_cli/09_host_commands.html",
    "c": []
   },
   {
    "t": "环境变量",
    "f": "content/04_cli/10_env_vars.html",
    "c": []
   }
  ]
 },
 {
  "t": "插件参考",
  "f": null,
  "c": [
   {
    "t": "插件参考总览",
    "f": "content/05_plugins/01_overview.html",
    "c": [
     {
      "t": "sax — SA UI 方言插件",
      "f": "content/05_plugins/02_sax.html",
      "c": []
     },
     {
      "t": "react — SAX 上的 React 兼容层",
      "f": "content/05_plugins/03_react.html",
      "c": []
     },
     {
      "t": "mui — SAX 版 Material UI 组件库",
      "f": "content/05_plugins/04_mui.html",
      "c": []
     },
     {
      "t": "vite — SAX 热重载开发服务器",
      "f": "content/05_plugins/05_vite.html",
      "c": []
     },
     {
      "t": "tui — 终端原语插件",
      "f": "content/05_plugins/06_tui.html",
      "c": []
     },
     {
      "t": "wgpu — 浏览器 WebGPU sidecar",
      "f": "content/05_plugins/07_wgpu.html",
      "c": []
     },
     {
      "t": "3dengines — 3D 引擎插件族",
      "f": "content/05_plugins/08_3dengines.html",
      "c": []
     },
     {
      "t": "vm — 动态解释器虚拟机",
      "f": "content/05_plugins/09_vm.html",
      "c": []
     },
     {
      "t": "sla — SLA 编译器插件（概述）",
      "f": "content/05_plugins/10_sla.html",
      "c": []
     },
     {
      "t": "deno — Deno 兼容 API 插件",
      "f": "content/05_plugins/11_deno.html",
      "c": []
     },
     {
      "t": "node — Node.js 兼容门面",
      "f": "content/05_plugins/12_node.html",
      "c": []
     },
     {
      "t": "pkg — 零信任包管理器",
      "f": "content/05_plugins/13_pkg.html",
      "c": []
     },
     {
      "t": "http-client — HTTP 客户端插件",
      "f": "content/05_plugins/14_http_client.html",
      "c": []
     },
     {
      "t": "http-server — 内嵌 HTTP 服务端插件",
      "f": "content/05_plugins/15_http_server.html",
      "c": []
     },
     {
      "t": "db — 本地列式数据库插件",
      "f": "content/05_plugins/16_db.html",
      "c": []
     },
     {
      "t": "bc2sa — LLVM bitcode 逆向翻译器",
      "f": "content/05_plugins/17_bc2sa.html",
      "c": [
       {
        "t": "FFI vs bc2sa：外部代码接入路径",
        "f": "content/05_plugins/18_ffi_vs_bc2sa.html",
        "c": []
       }
      ]
     }
    ]
   }
  ]
 },
 {
  "t": "db 数据库插件",
  "f": null,
  "c": [
   {
    "t": "db 插件总览：定位与架构",
    "f": "content/10_db/01_overview.html",
    "c": [
     {
      "t": "CLI 命令详解",
      "f": "content/10_db/02_cli.html",
      "c": []
     },
     {
      "t": "SA API 八大分组",
      "f": "content/10_db/03_api.html",
      "c": []
     },
     {
      "t": "宏用法与完整示例",
      "f": "content/10_db/04_macros_usage.html",
      "c": []
     },
     {
      "t": "vs SQLite：选型对比",
      "f": "content/10_db/05_vs_sqlite.html",
      "c": []
     },
     {
      "t": "边界、性能与最佳实践",
      "f": "content/10_db/06_limits_perf.html",
      "c": []
     }
    ]
   }
  ]
 },
 {
  "t": "ECS 开发（sla_ecs）",
  "f": null,
  "c": [
   {
    "t": "sla_ecs 是什么：定位与规模",
    "f": "content/11_ecs/01_overview.html",
    "c": [
     {
      "t": "架构与模块面",
      "f": "content/11_ecs/02_architecture.html",
      "c": []
     },
     {
      "t": "宏使用格局与编译器改进路线",
      "f": "content/11_ecs/03_macros.html",
      "c": []
     },
     {
      "t": "SA 层的 3d_ecs 插件契约",
      "f": "content/11_ecs/04_sa3d_ecs.html",
      "c": []
     },
     {
      "t": "已知问题与回归史",
      "f": "content/11_ecs/05_status.html",
      "c": []
     }
    ]
   }
  ]
 },
 {
  "t": "标准库",
  "f": null,
  "c": [
   {
    "t": "标准库总览",
    "f": "content/06_stdlib/01_overview.html",
    "c": [
     {
      "t": "如何使用 sa_std：导入机制与契约体系",
      "f": "content/06_stdlib/13_usage_guide.html",
      "c": []
     },
     {
      "t": "常见配方：从打印到 HTTP 的完整示例",
      "f": "content/06_stdlib/14_recipes.html",
      "c": []
     },
     {
      "t": "io 与 print：标准输入输出",
      "f": "content/06_stdlib/02_io_print.html",
      "c": []
     },
     {
      "t": "fmt：数值与字节格式化",
      "f": "content/06_stdlib/03_fmt.html",
      "c": []
     },
     {
      "t": "string：ASCII / UTF-8 字符串",
      "f": "content/06_stdlib/04_string.html",
      "c": []
     },
     {
      "t": "collections：Vec / HashMap / Option 等",
      "f": "content/06_stdlib/05_collections.html",
      "c": []
     },
     {
      "t": "fs：文件与目录",
      "f": "content/06_stdlib/06_fs.html",
      "c": []
     },
     {
      "t": "env：环境变量与目录",
      "f": "content/06_stdlib/07_env.html",
      "c": []
     },
     {
      "t": "time：时钟、时间与睡眠",
      "f": "content/06_stdlib/08_time.html",
      "c": []
     },
     {
      "t": "process：子进程",
      "f": "content/06_stdlib/09_process.html",
      "c": []
     },
     {
      "t": "net：TCP / UDP / Unix 套接字与 HTTP/2",
      "f": "content/06_stdlib/10_net.html",
      "c": []
     },
     {
      "t": "encoding 与 text：JSON 与正则",
      "f": "content/06_stdlib/11_encoding.html",
      "c": []
     },
     {
      "t": "term / fd / thread / testing",
      "f": "content/06_stdlib/12_term_fd_thread.html",
      "c": []
     }
    ]
   },
   {
    "t": "API 总索引",
    "f": "content/06_stdlib/15_api_index.html",
    "c": [
     {
      "t": "extern 函数契约全表",
      "f": "content/06_stdlib/16_api_externs.html",
      "c": []
     },
     {
      "t": "汇编宏清单",
      "f": "content/06_stdlib/17_api_macros.html",
      "c": []
     },
     {
      "t": "布局常量清单",
      "f": "content/06_stdlib/18_api_layout.html",
      "c": []
     }
    ]
   }
  ]
 },
 {
  "t": "SAX / MUI 界面开发",
  "f": null,
  "c": [
   {
    "t": "SAX 是什么与开发模型",
    "f": "content/07_ui/01_overview.html",
    "c": []
   },
   {
    "t": "SAX 语法规则",
    "f": "content/07_ui/02_syntax.html",
    "c": []
   },
   {
    "t": "项目结构约定",
    "f": "content/07_ui/03_project_structure.html",
    "c": []
   },
   {
    "t": "样式体系",
    "f": "content/07_ui/04_styling.html",
    "c": []
   },
   {
    "t": "组件库 mui 概览",
    "f": "content/07_ui/05_mui.html",
    "c": []
   },
   {
    "t": "react/vite 插件集成与本地预览",
    "f": "content/07_ui/06_toolchain.html",
    "c": []
   },
   {
    "t": "从零新建一个 SAX 界面工程",
    "f": "content/07_ui/07_getting_started.html",
    "c": []
   }
  ]
 },
 {
  "t": "FAQ 与故障排查",
  "f": null,
  "c": [
   {
    "t": "常见问题 FAQ",
    "f": "content/08_faq/01_faq.html",
    "c": []
   },
   {
    "t": "编译失败排查",
    "f": "content/08_faq/02_compile_failures.html",
    "c": []
   },
   {
    "t": "运行与环境问题排查",
    "f": "content/08_faq/03_runtime_env.html",
    "c": []
   },
   {
    "t": "性能与优化预期",
    "f": "content/08_faq/04_performance.html",
    "c": []
   },
   {
    "t": "当前局限与路线图状态",
    "f": "content/08_faq/05_limitations_roadmap.html",
    "c": []
   }
  ]
 }
];