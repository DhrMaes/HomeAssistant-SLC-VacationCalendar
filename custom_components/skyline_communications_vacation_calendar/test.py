from datetime import datetime
from CalendarApi import CalendarHelper, CalendarEntryType

helper = CalendarHelper("uhhFw2zWsM2OSAwOpdKcbmPFddVhMHbSUaKSm/fTYRA=")
entries = helper.get_entries("Frederic Anthierens", "477/147")

now = datetime.now()

holiday_types = [
    CalendarEntryType.Absent,
    CalendarEntryType.Public_Holiday,
    CalendarEntryType.Weekend,
]

matching_entries = [
    entry
    for entry in entries
    if entry.event_date <= now <= entry.end_date
    and entry.category in holiday_types
]

if matching_entries:
    print(False)
else:
    print(True)

for entry in entries:
    print(f"{entry.id}: {entry.category}")

print(helper.authenticate())