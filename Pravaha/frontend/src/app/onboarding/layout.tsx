import { AppShell } from "@/components/AppShell";

export default function OnboardingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <AppShell>{children}</AppShell>;
}
