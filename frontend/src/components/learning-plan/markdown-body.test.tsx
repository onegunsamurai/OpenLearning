import { render, screen } from "@testing-library/react";
import { MarkdownBody } from "./markdown-body";

describe("MarkdownBody", () => {
  it("renders plain text as paragraph", () => {
    render(<MarkdownBody content="Hello world" />);
    expect(screen.getByText("Hello world")).toBeInTheDocument();
  });

  it("renders markdown bold", () => {
    render(<MarkdownBody content="This is **bold** text" />);
    expect(screen.getByText("bold").tagName).toBe("STRONG");
  });

  it("renders markdown links", () => {
    render(<MarkdownBody content="Visit [example](https://example.com)" />);
    const link = screen.getByRole("link", { name: "example" });
    expect(link).toHaveAttribute("href", "https://example.com");
  });

  it("strips script tags (XSS prevention)", () => {
    const { container } = render(
      <MarkdownBody content='Some text <script>alert("xss")</script>' />
    );
    expect(container.querySelector("script")).toBeNull();
    expect(container.innerHTML).not.toContain("<script>");
  });

  it("strips img onerror (XSS prevention)", () => {
    const { container } = render(
      <MarkdownBody content='<img onerror="alert(1)" src="x">After' />
    );
    const img = container.querySelector("img");
    // rehype-sanitize allows img but strips onerror
    if (img) {
      expect(img.getAttribute("onerror")).toBeNull();
    }
  });

  it("strips iframe tags", () => {
    const { container } = render(
      <MarkdownBody content='<iframe src="https://evil.com"></iframe>Safe' />
    );
    expect(container.querySelector("iframe")).toBeNull();
  });

  it("strips javascript: URIs in links", () => {
    const { container } = render(
      <MarkdownBody content='<a href="javascript:alert(1)">Click</a>' />
    );
    const links = container.querySelectorAll("a");
    links.forEach((link) => {
      expect(link.getAttribute("href") ?? "").not.toContain("javascript:");
    });
  });

  it("renders code blocks", () => {
    render(<MarkdownBody content={"```\nconst x = 1;\n```"} />);
    expect(screen.getByText("const x = 1;")).toBeInTheDocument();
  });
});
