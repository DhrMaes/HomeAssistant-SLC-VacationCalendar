from CalendarApi import CalendarHelper

helper = CalendarHelper("uhhFw2zWsM2OSAwOpdKcbmPFddVhMHbSUaKSm/fTYRA=", "477/147")
entries = helper.getEntries("Arne Maes")

for entry in entries:
    print(f"{entry.id}: {entry.category}")

print(helper.authenticate())