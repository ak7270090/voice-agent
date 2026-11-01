import { TIME_ZONE_CHOICES } from "@/lib/constants";

/** A list of common zones; a zone saved earlier that is not in it stays selectable. */
export function TimeZoneSelect({
  value,
  className,
  onChange,
}: {
  value: string;
  className: string;
  onChange: (zone: string) => void;
}) {
  const known = TIME_ZONE_CHOICES.some((choice) => choice.value === value);
  return (
    <select className={className} value={value} onChange={(e) => onChange(e.target.value)}>
      {!known && value && <option value={value}>{value}</option>}
      {TIME_ZONE_CHOICES.map((choice) => (
        <option key={choice.value} value={choice.value}>
          {choice.label}
        </option>
      ))}
    </select>
  );
}
