import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RoleSelector } from "./role-selector";

vi.mock("@/lib/api", () => ({
  api: {
    getRoles: vi.fn().mockResolvedValue([
      {
        id: "backend_engineering",
        name: "Backend Engineer",
        description: "Backend engineering concepts",
        skillCount: 18,
        levels: ["junior", "mid", "senior", "staff"],
      },
      {
        id: "frontend_engineering",
        name: "Frontend Engineer",
        description: "Frontend engineering concepts",
        skillCount: 12,
        levels: ["junior", "mid", "senior", "staff"],
      },
      {
        id: "devops_engineering",
        name: "DevOps / Platform Engineer",
        description: "DevOps and platform engineering concepts",
        skillCount: 10,
        levels: ["junior", "mid", "senior", "staff"],
      },
    ]),
    getRole: vi.fn().mockResolvedValue({
      id: "backend_engineering",
      name: "Backend Engineer",
      description: "Backend engineering concepts",
      mappedSkillIds: ["nodejs", "python", "rest-api"],
      levels: [
        { name: "junior", conceptCount: 15 },
        { name: "mid", conceptCount: 15 },
        { name: "senior", conceptCount: 15 },
        { name: "staff", conceptCount: 15 },
      ],
    }),
  },
}));

describe("RoleSelector", () => {
  const defaultProps = {
    selectedRoleId: null,
    onSelectRole: vi.fn(),
    targetLevel: "mid",
    onTargetLevelChange: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders loading state initially", () => {
    render(<RoleSelector {...defaultProps} />);
    expect(screen.getByText("Loading roles...")).toBeInTheDocument();
  });

  it("renders role cards after fetch", async () => {
    render(<RoleSelector {...defaultProps} />);
    await waitFor(() => {
      expect(screen.getByText("Backend Engineer")).toBeInTheDocument();
    });
    expect(screen.getByText("Frontend Engineer")).toBeInTheDocument();
    expect(
      screen.getByText("DevOps / Platform Engineer")
    ).toBeInTheDocument();
  });

  it("highlights selected role", async () => {
    render(
      <RoleSelector
        {...defaultProps}
        selectedRoleId="backend_engineering"
      />
    );
    await waitFor(() => {
      expect(screen.getByText("Backend Engineer")).toBeInTheDocument();
    });
    const card = screen.getByText("Backend Engineer").closest("button");
    expect(card?.className).toContain("border-cyan");
  });

  it("calls onSelectRole with correct roleId and skillIds", async () => {
    const user = userEvent.setup();
    render(<RoleSelector {...defaultProps} />);
    await waitFor(() => {
      expect(screen.getByText("Backend Engineer")).toBeInTheDocument();
    });
    await user.click(screen.getByText("Backend Engineer"));
    await waitFor(() => {
      expect(defaultProps.onSelectRole).toHaveBeenCalledWith(
        "backend_engineering",
        ["nodejs", "python", "rest-api"]
      );
    });
  });

  it("renders all 4 level buttons", async () => {
    render(<RoleSelector {...defaultProps} />);
    await waitFor(() => {
      expect(screen.getByText("Junior")).toBeInTheDocument();
    });
    expect(screen.getByText("Mid")).toBeInTheDocument();
    expect(screen.getByText("Senior")).toBeInTheDocument();
    expect(screen.getByText("Staff")).toBeInTheDocument();
  });

  it("calls onTargetLevelChange when clicking level", async () => {
    const user = userEvent.setup();
    render(<RoleSelector {...defaultProps} />);
    await waitFor(() => {
      expect(screen.getByText("Senior")).toBeInTheDocument();
    });
    await user.click(screen.getByText("Senior"));
    expect(defaultProps.onTargetLevelChange).toHaveBeenCalledWith("senior");
  });

  it("renders error state", async () => {
    const { api } = await import("@/lib/api");
    vi.mocked(api.getRoles).mockRejectedValueOnce(new Error("Network error"));
    render(<RoleSelector {...defaultProps} />);
    await waitFor(() => {
      expect(screen.getByText("Network error")).toBeInTheDocument();
    });
  });
});
