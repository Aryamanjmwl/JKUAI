// @vitest-environment jsdom
import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import DocumentUpload from "./DocumentUpload";
import { uploadDocument } from "./api";

vi.mock("./api", () => ({ uploadDocument: vi.fn() }));
afterEach(() => { cleanup(); vi.clearAllMocks(); });

it("uploads a PDF without asking for an OpenAI key and reports success", async () => {
  vi.mocked(uploadDocument).mockResolvedValue({ document_id: "id", title: "Course guide", chunks_created: 3, duplicate: false });
  const completed = vi.fn();
  const user = userEvent.setup();
  render(<DocumentUpload groups={[]} demoRolesEnabled={false} onUploaded={completed} onBusyChange={vi.fn()} />);
  const file = new File(["PDF bytes"], "course-guide.pdf", { type: "application/pdf" });
  await user.upload(screen.getByLabelText("PDF file"), file);
  expect((screen.getByLabelText("Document title") as HTMLInputElement).value).toBe("course guide");
  // Exercise the React submit handler; Chromium covers native file-input validation.
  fireEvent.submit(screen.getByRole("button", { name: "Upload PDF" }).closest("form")!);
  expect(await screen.findByText(/3 searchable passages/)).toBeTruthy();
  expect(uploadDocument).toHaveBeenCalledWith(expect.objectContaining({ file, visibility: "public", allowedGroups: "" }), []);
  expect(completed).toHaveBeenCalledOnce();
});

it("passes explicit restricted groups and the current simulated identity", async () => {
  vi.mocked(uploadDocument).mockResolvedValue({ document_id: "id", title: "Staff", chunks_created: 1, duplicate: true });
  const user = userEvent.setup();
  render(<DocumentUpload groups={["staff"]} demoRolesEnabled onUploaded={vi.fn()} onBusyChange={vi.fn()} />);
  await user.upload(screen.getByLabelText("PDF file"), new File(["bytes"], "staff.pdf", { type: "application/pdf" }));
  await user.selectOptions(screen.getByLabelText("Who can retrieve this document?"), "restricted");
  await user.type(screen.getByLabelText("Allowed groups"), "staff, admissions");
  // Exercise the React submit handler; Chromium covers native file-input validation.
  fireEvent.submit(screen.getByRole("button", { name: "Upload PDF" }).closest("form")!);
  expect(await screen.findByText(/already indexed/)).toBeTruthy();
  expect(uploadDocument).toHaveBeenCalledWith(expect.objectContaining({ visibility: "restricted", allowedGroups: "staff, admissions" }), ["staff"]);
});

it("shows ingestion errors and permits retry", async () => {
  vi.mocked(uploadDocument).mockRejectedValue(new Error("No extractable text found in PDF"));
  const user = userEvent.setup();
  render(<DocumentUpload groups={[]} demoRolesEnabled={false} onUploaded={vi.fn()} onBusyChange={vi.fn()} />);
  await user.upload(screen.getByLabelText("PDF file"), new File(["bytes"], "scan.pdf", { type: "application/pdf" }));
  // Exercise the React submit handler; Chromium covers native file-input validation.
  fireEvent.submit(screen.getByRole("button", { name: "Upload PDF" }).closest("form")!);
  expect(await screen.findByRole("alert")).toHaveProperty("textContent", "No extractable text found in PDF");
  expect((screen.getByRole("button", { name: "Upload PDF" }) as HTMLButtonElement).disabled).toBe(false);
});
