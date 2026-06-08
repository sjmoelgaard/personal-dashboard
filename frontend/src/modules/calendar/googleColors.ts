export const GOOGLE_COLORS: Record<string, string> = {
  '1': '#D50000',   // Tomat
  '2': '#E67C73',   // Flamingo
  '3': '#8E24AA',   // Drue
  '4': '#3F51B5',   // Blåbær
  '5': '#039BE5',   // Hav
  '6': '#33B679',   // Salvie
  '7': '#0B8043',   // Basilikum
  '8': '#7CB342',   // Avocado
  '9': '#F6BF26',   // Fersken
  '10': '#F09300',  // Banan
  '11': '#616161',  // Grafit
}

export const GOOGLE_COLOR_NAMES: Record<string, string> = {
  '1': 'Tomat', '2': 'Flamingo', '3': 'Drue', '4': 'Blåbær',
  '5': 'Hav', '6': 'Salvie', '7': 'Basilikum', '8': 'Avocado',
  '9': 'Fersken', '10': 'Banan', '11': 'Grafit',
}

export function resolveEventColor(event: {
  google_color_id: string | null
  source_color: string | null
}): string {
  if (event.google_color_id && GOOGLE_COLORS[event.google_color_id]) {
    return GOOGLE_COLORS[event.google_color_id]
  }
  return event.source_color ?? '#eab308'
}
