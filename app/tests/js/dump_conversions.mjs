// Prints [gregorianIso, jalaliKey] for every day from 1990-01-01 to 2060-12-31 as JSON.
import { JalaliCalendar } from '../../restaurant/static/js/modules/jalali-calendar.js';

const pairs = [];
const cursor = new Date(Date.UTC(1990, 0, 1));
const last = new Date(Date.UTC(2060, 11, 31));
while (cursor <= last) {
  // Date.UTC avoids any local time zone shift; the calendar reads local fields, so build a local noon date.
  const local = new Date(cursor.getUTCFullYear(), cursor.getUTCMonth(), cursor.getUTCDate(), 12);
  const jalali = JalaliCalendar.fromDate(local);
  pairs.push([cursor.toISOString().slice(0, 10), JalaliCalendar.toKey(jalali), JalaliCalendar.toIso(jalali)]);
  cursor.setUTCDate(cursor.getUTCDate() + 1);
}
console.log(JSON.stringify(pairs));
