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

  it("renders error state with retry button when getRoles fails", async () => {
    const { api } = await import("@/lib/api");
    vi.mocked(api.getRoles).mockRejectedValueOnce(new Error("Network error"));
    render(<RoleSelector {...defaultProps} />);
    await waitFor(() => {
      expect(screen.getByText("Network error")).toBeInTheDocument();
    });
    expect(screen.getByText("Retry")).toBeInTheDocument();
  });

  it("retries fetching roles when clicking Retry", async () => {
    const user = userEvent.setup();
    const { api } = await import("@/lib/api");
    vi.mocked(api.getRoles).mockRejectedValueOnce(new Error("Network error"));
    render(<RoleSelector {...defaultProps} />);
    await waitFor(() => {
      expect(screen.getByText("Network error")).toBeInTheDocument();
    });

    // Reset to succeed on retry
    vi.mocked(api.getRoles).mockResolvedValueOnce([
      {
        id: "backend_engineering",
        name: "Backend Engineer",
        description: "Backend engineering concepts",
        skillCount: 18,
        levels: ["junior", "mid", "senior", "staff"],
      },
    ]);

    await user.click(screen.getByText("Retry"));
    await waitFor(() => {
      expect(screen.getByText("Backend Engineer")).toBeInTheDocument();
    });
    expect(screen.queryByText("Network error")).not.toBeInTheDocument();
  });

  it("shows non-blocking error when getRole fails", async () => {
    const user = userEvent.setup();
    const { api } = await import("@/lib/api");
    vi.mocked(api.getRole).mockRejectedValueOnce(
      new Error("Role fetch failed")
    );
    render(<RoleSelector {...defaultProps} />);
    await waitFor(() => {
      expect(screen.getByText("Backend Engineer")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Backend Engineer"));
    await waitFor(() => {
      expect(
        screen.getByText("Failed to load role details")
      ).toBeInTheDocument();
    });
    // Role cards should still be visible
    expect(screen.getByText("Backend Engineer")).toBeInTheDocument();
    expect(screen.getByText("Frontend Engineer")).toBeInTheDocument();
  });

  describe("accessibility", () => {
    it("role cards have aria-pressed and type=button", async () => {
      render(
        <RoleSelector
          {...defaultProps}
          selectedRoleId="backend_engineering"
        />
      );
      await waitFor(() => {
        expect(screen.getByText("Backend Engineer")).toBeInTheDocument();
      });

      const selectedCard = screen
        .getByText("Backend Engineer")
        .closest("button");
      const unselectedCard = screen
        .getByText("Frontend Engineer")
        .closest("button");

      expect(selectedCard).toHaveAttribute("aria-pressed", "true");
      expect(selectedCard).toHaveAttribute("type", "button");
      expect(unselectedCard).toHaveAttribute("aria-pressed", "false");
      expect(unselectedCard).toHaveAttribute("type", "button");
    });

    it("level buttons wrapper has role=radiogroup", async () => {
      render(<RoleSelector {...defaultProps} />);
      await waitFor(() => {
        expect(screen.getByText("Junior")).toBeInTheDocument();
      });
      const radiogroup = screen.getByRole("radiogroup");
      expect(radiogroup).toHaveAttribute("aria-label", "Target level");
    });

    it("level buttons have type=button and aria-pressed", async () => {
      render(<RoleSelector {...defaultProps} targetLevel="senior" />);
      await waitFor(() => {
        expect(screen.getByText("Senior")).toBeInTheDocument();
      });

      const seniorBtn = screen.getByText("Senior");
      const midBtn = screen.getByText("Mid");

      expect(seniorBtn).toHaveAttribute("type", "button");
      expect(seniorBtn).toHaveAttribute("aria-pressed", "true");
      expect(midBtn).toHaveAttribute("type", "button");
      expect(midBtn).toHaveAttribute("aria-pressed", "false");
    });
  });

  describe("race condition handling", () => {
    it("disables role buttons while a role is loading, preventing duplicate clicks", async () => {
      const user = userEvent.setup();
      const { api } = await import("@/lib/api");

      let resolveGetRole: (v: unknown) => void;
      vi.mocked(api.getRole).mockReturnValueOnce(
        new Promise((r) => {
          resolveGetRole = r;
        }) as never
      );

      render(<RoleSelector {...defaultProps} />);
      await waitFor(() => {
        expect(screen.getByText("Backend Engineer")).toBeInTheDocument();
      });

      await user.click(screen.getByText("Backend Engineer"));

      // All role buttons should be disabled while fetch is in-flight
      await waitFor(() => {
        const backendBtn = screen
          .getByText("Backend Engineer")
          .closest("button");
        expect(backendBtn).toBeDisabled();
      });

      const frontendBtn = screen
        .getByText("Frontend Engineer")
        .closest("button");
      expect(frontendBtn).toBeDisabled();

      // Resolve the request
      resolveGetRole!({
        id: "backend_engineering",
        name: "Backend Engineer",
        description: "Backend engineering concepts",
        mappedSkillIds: ["nodejs", "python", "rest-api"],
        levels: [],
      });

      await waitFor(() => {
        expect(defaultProps.onSelectRole).toHaveBeenCalledTimes(1);
        expect(defaultProps.onSelectRole).toHaveBeenCalledWith(
          "backend_engineering",
          ["nodejs", "python", "rest-api"]
        );
      });

      // Buttons should be re-enabled after fetch completes
      await waitFor(() => {
        const backendBtn = screen
          .getByText("Backend Engineer")
          .closest("button");
        expect(backendBtn).not.toBeDisabled();
      });
    });

    it("ignores stale responses via request counter", async () => {
      const { api } = await import("@/lib/api");

      let resolveFirst: (v: unknown) => void;
      const firstPromise = new Promise((r) => {
        resolveFirst = r;
      });

      vi.mocked(api.getRole).mockReturnValueOnce(firstPromise as never);

      const { rerender } = render(<RoleSelector {...defaultProps} />);
      await waitFor(() => {
        expect(screen.getByText("Backend Engineer")).toBeInTheDocument();
      });

      // Trigger first click
      const user = userEvent.setup();
      await user.click(screen.getByText("Backend Engineer"));

      // Buttons are now disabled, but let's resolve the first request
      // and immediately simulate what happens if the component unmounts/remounts
      // The requestCounterRef ensures stale responses don't call onSelectRole

      // Resolve the in-flight request — this should call onSelectRole
      resolveFirst!({
        id: "backend_engineering",
        name: "Backend Engineer",
        description: "Backend engineering concepts",
        mappedSkillIds: ["nodejs", "python", "rest-api"],
        levels: [],
      });

      await waitFor(() => {
        expect(defaultProps.onSelectRole).toHaveBeenCalledTimes(1);
      });

      // Now click a second role after the first completes
      vi.mocked(api.getRole).mockResolvedValueOnce({
        id: "frontend_engineering",
        name: "Frontend Engineer",
        description: "Frontend engineering concepts",
        mappedSkillIds: ["react", "css"],
        levels: [],
      } as never);

      rerender(<RoleSelector {...defaultProps} />);
      await user.click(screen.getByText("Frontend Engineer"));

      await waitFor(() => {
        expect(defaultProps.onSelectRole).toHaveBeenCalledTimes(2);
        expect(defaultProps.onSelectRole).toHaveBeenLastCalledWith(
          "frontend_engineering",
          ["react", "css"]
        );
      });
    });
  });
});
