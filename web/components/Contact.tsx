import { CONTACT_EMAIL } from "@/lib/site";

export default function Contact() {
  return CONTACT_EMAIL ? (
    <p>
      Questions or requests: <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>.
    </p>
  ) : (
    <p>Questions or requests: use the feedback box on the ledger page.</p>
  );
}
