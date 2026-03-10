export function parseCsv(text: string): Array<Record<string, string>> {
  const lines = text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line.length > 0);
  if (lines.length === 0) {
    return [];
  }
  const headers = lines[0].split(",").map((item) => item.trim());
  return lines.slice(1).map((line) => {
    const values = line.split(",");
    const row: Record<string, string> = {};
    for (let index = 0; index < headers.length; index += 1) {
      row[headers[index]] = (values[index] ?? "").trim();
    }
    return row;
  });
}
