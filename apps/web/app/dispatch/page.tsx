import { DispatchWorkbench } from "@/components/dispatch-workbench";

export default async function DispatchPage({
  searchParams,
}: {
  searchParams: Promise<{ ticket?: string | string[] }>;
}) {
  const value = (await searchParams).ticket;
  const initialTicketId = typeof value === "string" ? value : undefined;

  return <DispatchWorkbench initialTicketId={initialTicketId} />;
}
