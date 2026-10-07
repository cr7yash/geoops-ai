import { TicketDetailView } from "@/components/ticket-detail";

export default async function TicketPage({
  params,
}: PageProps<"/tickets/[ticketId]">) {
  const { ticketId } = await params;
  return <TicketDetailView ticketId={ticketId} />;
}
