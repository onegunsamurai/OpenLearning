import { render, screen } from "@testing-library/react";
import { ChatMessage } from "./ChatMessage";

describe("ChatMessage", () => {
  it("renders assistant message content", () => {
    render(<ChatMessage role="assistant" content="Hello there" />);
    expect(screen.getByText("Hello there")).toBeInTheDocument();
  });

  it("renders user message content", () => {
    render(<ChatMessage role="user" content="My answer" />);
    expect(screen.getByText("My answer")).toBeInTheDocument();
  });

  it("shows Bot icon for assistant, not User icon", () => {
    const { container } = render(
      <ChatMessage role="assistant" content="Hi" />
    );
    // Bot icon should be present (lucide renders an svg with class)
    expect(container.querySelector(".lucide-bot")).toBeInTheDocument();
    expect(container.querySelector(".lucide-user")).not.toBeInTheDocument();
  });

  it("shows User icon for user, not Bot icon", () => {
    const { container } = render(
      <ChatMessage role="user" content="Hi" />
    );
    expect(container.querySelector(".lucide-user")).toBeInTheDocument();
    expect(container.querySelector(".lucide-bot")).not.toBeInTheDocument();
  });

  it("left-aligns assistant messages", () => {
    const { container } = render(
      <ChatMessage role="assistant" content="Hi" />
    );
    const wrapper = container.firstElementChild;
    expect(wrapper?.className).toContain("justify-start");
  });

  it("right-aligns user messages", () => {
    const { container } = render(
      <ChatMessage role="user" content="Hi" />
    );
    const wrapper = container.firstElementChild;
    expect(wrapper?.className).toContain("justify-end");
  });

  it("preserves whitespace in content", () => {
    const { container } = render(
      <ChatMessage role="assistant" content={"line1\n  line2"} />
    );
    const pre = container.querySelector(".whitespace-pre-wrap");
    expect(pre).toBeInTheDocument();
    expect(pre?.textContent).toBe("line1\n  line2");
  });

  it("applies card background to assistant bubble", () => {
    const { container } = render(
      <ChatMessage role="assistant" content="Hi" />
    );
    const bubble = container.querySelector(".whitespace-pre-wrap")
      ?.parentElement;
    expect(bubble?.className).toContain("bg-card");
    expect(bubble?.className).not.toContain("bg-cyan");
  });

  it("applies cyan background to user bubble", () => {
    const { container } = render(
      <ChatMessage role="user" content="Hi" />
    );
    const bubble = container.querySelector(".whitespace-pre-wrap")
      ?.parentElement;
    expect(bubble?.className).toContain("bg-cyan");
    expect(bubble?.className).not.toContain("bg-card");
  });

  it("renders with empty content", () => {
    const { container } = render(
      <ChatMessage role="assistant" content="" />
    );
    const pre = container.querySelector(".whitespace-pre-wrap");
    expect(pre).toBeInTheDocument();
    expect(pre?.textContent).toBe("");
  });
});
