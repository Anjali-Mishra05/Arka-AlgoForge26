import { redirect } from "next/navigation";

export default async function SignupRedirect({
  searchParams,
}: {
  searchParams: Promise<{ next?: string }>;
}) {
  const params = await searchParams;
  const nextPath = params?.next;

  redirect(nextPath ? `/sign-up?next=${encodeURIComponent(nextPath)}` : "/sign-up");
}
