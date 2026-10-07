import { TechnicianDetailView } from "@/components/technician-detail";

export default async function TechnicianPage({
  params,
}: PageProps<"/technicians/[technicianId]">) {
  const { technicianId } = await params;
  return <TechnicianDetailView technicianId={technicianId} />;
}
