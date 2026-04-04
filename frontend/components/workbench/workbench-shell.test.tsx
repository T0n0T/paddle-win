import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, vi } from "vitest";

import { WorkbenchShell } from "./workbench-shell";

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

test("creates a session and renders preview and change summary", async () => {
  const fetchMock = vi
    .fn()
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          session_id: "s1",
          version: 1,
          image_path: "/tmp/form.png",
          ocr_json_path: "/tmp/ocr.json",
          current_html: "<form><input aria-label='姓名' /></form>",
          current_form_json: {
            title: "客户登记表",
            description: "",
            sections: [],
            fields: [],
          },
          summary: {
            user_intent: "初始化",
            applied: ["生成首版"],
            warnings: [],
            unresolved: [],
            touched_field_ids: [],
          },
          turns: [
            {
              user_message: "初始化",
              assistant_message: null,
              html: "<form><input aria-label='姓名' /></form>",
              form_document: {
                title: "客户登记表",
                description: "",
                sections: [],
                fields: [],
              },
              summary: {
                user_intent: "初始化",
                applied: ["生成首版"],
                warnings: [],
                unresolved: [],
                touched_field_ids: [],
              },
            },
          ],
        }),
        { status: 200 },
      ),
    )
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          session_id: "s1",
          version: 2,
          image_path: "/tmp/form.png",
          ocr_json_path: "/tmp/ocr.json",
          current_html:
            "<form><input aria-label='姓名' /><textarea aria-label='备注'></textarea></form>",
          current_form_json: {
            title: "客户登记表 v2",
            description: "",
            sections: [],
            fields: [],
          },
          summary: {
            user_intent: "新增备注",
            applied: ["新增备注字段"],
            warnings: [],
            unresolved: [],
            touched_field_ids: ["remark"],
          },
          turns: [
            {
              user_message: "初始化",
              assistant_message: null,
              html: "<form><input aria-label='姓名' /></form>",
              form_document: {
                title: "客户登记表",
                description: "",
                sections: [],
                fields: [],
              },
              summary: {
                user_intent: "初始化",
                applied: ["生成首版"],
                warnings: [],
                unresolved: [],
                touched_field_ids: [],
              },
            },
            {
              user_message: "新增备注框",
              assistant_message: "已新增备注字段",
              html: "<form><input aria-label='姓名' /><textarea aria-label='备注'></textarea></form>",
              form_document: {
                title: "客户登记表 v2",
                description: "",
                sections: [],
                fields: [],
              },
              summary: {
                user_intent: "新增备注",
                applied: ["新增备注字段"],
                warnings: [],
                unresolved: [],
                touched_field_ids: ["remark"],
              },
            },
          ],
        }),
        { status: 200 },
      ),
    );

  vi.stubGlobal("fetch", fetchMock);

  render(<WorkbenchShell />);

  fireEvent.change(screen.getByLabelText("表单图片路径"), {
    target: { value: "/tmp/form.png" },
  });
  fireEvent.change(screen.getByLabelText("OCR JSON 路径"), {
    target: { value: "/tmp/ocr.json" },
  });
  fireEvent.click(screen.getByRole("button", { name: "创建会话" }));

  await screen.findByTitle("表单预览");

  fireEvent.change(screen.getByLabelText("请输入修改指令"), {
    target: { value: "新增备注框" },
  });
  fireEvent.click(screen.getByRole("button", { name: "发送修改" }));

  await waitFor(() => {
    expect(screen.getByText("新增备注字段")).toBeInTheDocument();
  });
  expect(screen.getByTitle("表单预览")).toHaveAttribute(
    "srcdoc",
    expect.stringContaining("textarea"),
  );
});

test("rolls back to the previous version and restores the preview", async () => {
  const fetchMock = vi
    .fn()
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          session_id: "s1",
          version: 1,
          image_path: "/tmp/form.png",
          ocr_json_path: "/tmp/ocr.json",
          current_html: "<form><input aria-label='姓名' /></form>",
          current_form_json: {
            title: "客户登记表",
            description: "",
            sections: [],
            fields: [],
          },
          summary: {
            user_intent: "初始化",
            applied: ["生成首版"],
            warnings: [],
            unresolved: [],
            touched_field_ids: [],
          },
          turns: [
            {
              user_message: "初始化",
              assistant_message: null,
              html: "<form><input aria-label='姓名' /></form>",
              form_document: {
                title: "客户登记表",
                description: "",
                sections: [],
                fields: [],
              },
              summary: {
                user_intent: "初始化",
                applied: ["生成首版"],
                warnings: [],
                unresolved: [],
                touched_field_ids: [],
              },
            },
          ],
        }),
        { status: 200 },
      ),
    )
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          session_id: "s1",
          version: 2,
          image_path: "/tmp/form.png",
          ocr_json_path: "/tmp/ocr.json",
          current_html:
            "<form><input aria-label='姓名' /><textarea aria-label='备注'></textarea></form>",
          current_form_json: {
            title: "客户登记表 v2",
            description: "",
            sections: [],
            fields: [],
          },
          summary: {
            user_intent: "新增备注",
            applied: ["新增备注字段"],
            warnings: [],
            unresolved: [],
            touched_field_ids: ["remark"],
          },
          turns: [
            {
              user_message: "初始化",
              assistant_message: null,
              html: "<form><input aria-label='姓名' /></form>",
              form_document: {
                title: "客户登记表",
                description: "",
                sections: [],
                fields: [],
              },
              summary: {
                user_intent: "初始化",
                applied: ["生成首版"],
                warnings: [],
                unresolved: [],
                touched_field_ids: [],
              },
            },
            {
              user_message: "新增备注框",
              assistant_message: "已新增备注字段",
              html: "<form><input aria-label='姓名' /><textarea aria-label='备注'></textarea></form>",
              form_document: {
                title: "客户登记表 v2",
                description: "",
                sections: [],
                fields: [],
              },
              summary: {
                user_intent: "新增备注",
                applied: ["新增备注字段"],
                warnings: [],
                unresolved: [],
                touched_field_ids: ["remark"],
              },
            },
          ],
        }),
        { status: 200 },
      ),
    )
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          session_id: "s1",
          version: 1,
          image_path: "/tmp/form.png",
          ocr_json_path: "/tmp/ocr.json",
          current_html: "<form><input aria-label='姓名' /></form>",
          current_form_json: {
            title: "客户登记表",
            description: "",
            sections: [],
            fields: [],
          },
          summary: {
            user_intent: "回滚到上一版",
            applied: ["撤销新增备注字段"],
            warnings: [],
            unresolved: [],
            touched_field_ids: ["remark"],
          },
          turns: [
            {
              user_message: "初始化",
              assistant_message: null,
              html: "<form><input aria-label='姓名' /></form>",
              form_document: {
                title: "客户登记表",
                description: "",
                sections: [],
                fields: [],
              },
              summary: {
                user_intent: "初始化",
                applied: ["生成首版"],
                warnings: [],
                unresolved: [],
                touched_field_ids: [],
              },
            },
          ],
        }),
        { status: 200 },
      ),
    );

  vi.stubGlobal("fetch", fetchMock);

  render(<WorkbenchShell />);

  fireEvent.change(screen.getByLabelText("表单图片路径"), {
    target: { value: "/tmp/form.png" },
  });
  fireEvent.change(screen.getByLabelText("OCR JSON 路径"), {
    target: { value: "/tmp/ocr.json" },
  });
  fireEvent.click(screen.getByRole("button", { name: "创建会话" }));

  await screen.findByTitle("表单预览");

  fireEvent.change(screen.getByLabelText("请输入修改指令"), {
    target: { value: "新增备注框" },
  });
  fireEvent.click(screen.getByRole("button", { name: "发送修改" }));

  await waitFor(() => {
    expect(screen.getByText("新增备注字段")).toBeInTheDocument();
  });

  const preview = screen.getByTitle("表单预览");
  expect(preview).toHaveAttribute("srcdoc", expect.stringContaining("textarea"));
  expect(screen.getAllByText("版本 2").length).toBeGreaterThanOrEqual(1);

  fireEvent.click(screen.getByRole("button", { name: "回滚到上一版" }));

  await waitFor(() => {
    expect(screen.getAllByText("版本 1").length).toBeGreaterThanOrEqual(1);
  });
  expect(screen.getByTitle("表单预览")).toHaveAttribute(
    "srcdoc",
    "<form><input aria-label='姓名' /></form>",
  );
  expect(fetchMock).toHaveBeenNthCalledWith(
    3,
    "http://127.0.0.1:8000/api/sessions/s1/rollback",
    expect.objectContaining({
      method: "POST",
    }),
  );
});

test("shows an alert when sending a modification request fails", async () => {
  const fetchMock = vi
    .fn()
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          session_id: "s1",
          version: 1,
          image_path: "/tmp/form.png",
          ocr_json_path: "/tmp/ocr.json",
          current_html: "<form><input aria-label='姓名' /></form>",
          current_form_json: {
            title: "客户登记表",
            description: "",
            sections: [],
            fields: [],
          },
          summary: {
            user_intent: "初始化",
            applied: ["生成首版"],
            warnings: [],
            unresolved: [],
            touched_field_ids: [],
          },
          turns: [
            {
              user_message: "初始化",
              assistant_message: null,
              html: "<form><input aria-label='姓名' /></form>",
              form_document: {
                title: "客户登记表",
                description: "",
                sections: [],
                fields: [],
              },
              summary: {
                user_intent: "初始化",
                applied: ["生成首版"],
                warnings: [],
                unresolved: [],
                touched_field_ids: [],
              },
            },
          ],
        }),
        { status: 200 },
      ),
    )
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          detail: "模型服务暂时不可用",
        }),
        {
          status: 502,
          headers: {
            "Content-Type": "application/json",
          },
        },
      ),
    );

  vi.stubGlobal("fetch", fetchMock);

  render(<WorkbenchShell />);

  fireEvent.change(screen.getByLabelText("表单图片路径"), {
    target: { value: "/tmp/form.png" },
  });
  fireEvent.change(screen.getByLabelText("OCR JSON 路径"), {
    target: { value: "/tmp/ocr.json" },
  });
  fireEvent.click(screen.getByRole("button", { name: "创建会话" }));

  await screen.findByTitle("表单预览");

  fireEvent.change(screen.getByLabelText("请输入修改指令"), {
    target: { value: "新增备注框" },
  });
  fireEvent.click(screen.getByRole("button", { name: "发送修改" }));

  await waitFor(() => {
    expect(screen.getByRole("alert")).toHaveTextContent("模型服务暂时不可用");
  });
  expect(screen.getByLabelText("请输入修改指令")).toHaveValue("新增备注框");
  expect(screen.getByTitle("表单预览")).toHaveAttribute(
    "srcdoc",
    "<form><input aria-label='姓名' /></form>",
  );
});
