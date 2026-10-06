type NavIconName =
  "overview" | "tickets" | "technicians" | "agent" | "approvals";

export function MarkIcon() {
  return (
    <svg aria-hidden="true" className="mark-icon" viewBox="0 0 40 40">
      <path
        d="M20 3 34 11v18L20 37 6 29V11L20 3Z"
        fill="none"
        stroke="currentColor"
      />
      <path
        d="m13 16 7-4 7 4v8l-7 4-7-4v-8Z"
        fill="currentColor"
        opacity=".18"
      />
      <circle cx="20" cy="20" r="3.5" fill="currentColor" />
    </svg>
  );
}

export function NavIcon({ name }: { name: NavIconName }) {
  const paths: Record<NavIconName, React.ReactNode> = {
    overview: <path d="M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h6v6h-6z" />,
    tickets: <path d="M5 4h14v16H5zM8 8h8M8 12h8M8 16h5" />,
    technicians: (
      <path d="M16 19v-2a4 4 0 0 0-4-4H7a4 4 0 0 0-4 4v2M9.5 9a3 3 0 1 0 0-6 3 3 0 0 0 0 6ZM17 8v6M14 11h6" />
    ),
    agent: (
      <path d="M12 2v3M5 8l-2-2M19 6l-2 2M4 14H2M22 14h-2M7 14a5 5 0 1 1 10 0c0 2-1 3-2 4H9c-1-1-2-2-2-4ZM9 22h6" />
    ),
    approvals: <path d="M9 3h6l1 3h4v15H4V6h4l1-3ZM8 13l3 3 6-7" />,
  };

  return (
    <svg
      aria-hidden="true"
      className="nav-icon"
      fill="none"
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth="1.6"
      viewBox="0 0 24 24"
    >
      {paths[name]}
    </svg>
  );
}
