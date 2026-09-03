import { CopilotRuntime, createCopilotRuntimeHandler } from "@copilotkit/runtime/v2";
import { HttpAgent } from "@ag-ui/client";

// 1. Định nghĩa agent trỏ tới Python Backend dạng Object Key-Value theo đúng Type yêu cầu
const agentsConfig = {
  assistant: new HttpAgent({
    url: "http://127.0.0.1:8000/api/copilotkit",
  }) as any,
};

// 2. Khởi tạo instance với đúng cấu trúc Intelligence độc lập (Không kích hoạt enterprise channels)
const runtime = new CopilotRuntime({
  agents: agentsConfig,
});

// 3. Khởi tạo Handler kết nối App Router Next.js 
const handler = createCopilotRuntimeHandler({
  runtime,
  mode: "single-route",
  basePath: "/api/copilotkit",
});

export { handler as GET, handler as POST };
