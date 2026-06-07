import { Textarea } from "@/components/ui/textarea"
import {
  MATTER_DESCRIPTION_HINT,
  MATTER_DESCRIPTION_MAX,
  MATTER_DESCRIPTION_PLACEHOLDER,
} from "@/lib/matterConstants"

interface CaseNotesFieldProps {
  value: string
  onChange: (value: string) => void
  rows?: number
}

export function CaseNotesField({ value, onChange, rows = 4 }: CaseNotesFieldProps) {
  return (
    <div>
      <label className="text-xs font-medium text-slate-500">Case notes (used by AI in chat)</label>
      <p className="text-xs text-slate-400 mt-0.5 mb-1.5">{MATTER_DESCRIPTION_HINT}</p>
      <Textarea
        value={value}
        onChange={(e) => onChange(e.target.value.slice(0, MATTER_DESCRIPTION_MAX))}
        placeholder={MATTER_DESCRIPTION_PLACEHOLDER}
        rows={rows}
        className="min-h-[100px] mt-1"
      />
      <p className="text-xs text-slate-400 mt-1 text-right">
        {value.length}/{MATTER_DESCRIPTION_MAX}
      </p>
    </div>
  )
}
