// Run with: node --test tests/js
import assert from 'node:assert/strict';
import { test } from 'node:test';

import { JalaliCalendar } from '../../restaurant/static/js/modules/jalali-calendar.js';

test('Nowruz 1405 is 21 March 2026', () => {
  assert.equal(JalaliCalendar.toIso({ year: 1405, month: 1, day: 1 }), '2026-03-21');
});

test('leap years and month lengths', () => {
  assert.equal(JalaliCalendar.isLeapYear(1403), true);
  assert.equal(JalaliCalendar.isLeapYear(1404), false);
  assert.equal(JalaliCalendar.daysInMonth(1403, 12), 30);
  assert.equal(JalaliCalendar.daysInMonth(1404, 12), 29);
  assert.equal(JalaliCalendar.daysInMonth(1405, 1), 31);
  assert.equal(JalaliCalendar.daysInMonth(1405, 7), 30);
});

test('the week starts on Saturday and Friday is index 6', () => {
  const friday = { year: 1405, month: 8, day: 8 };
  assert.equal(JalaliCalendar.weekdayIndex(friday), 6);
  assert.equal(JalaliCalendar.weekdayIndex({ year: 1405, month: 8, day: 2 }), 0);
});

test('formatting in both languages', () => {
  const date = { year: 1405, month: 8, day: 4 };
  assert.equal(JalaliCalendar.formatDate(date, 'fa'), '۴ آبان ۱۴۰۵');
  assert.equal(JalaliCalendar.formatDate(date, 'en'), '4 Aban 1405');
  assert.equal(JalaliCalendar.formatNumeric(date, 'fa'), '۱۴۰۵/۰۸/۰۴');
  assert.equal(JalaliCalendar.formatNumeric(date, 'en'), '1405/08/04');
  assert.equal(JalaliCalendar.formatLong(date, 'en'), 'Monday, 4 Aban');
});

test('keys round-trip and invalid keys are rejected', () => {
  assert.deepEqual(JalaliCalendar.parseKey('۱۴۰۵/۰۸/۰۴'), { year: 1405, month: 8, day: 4 });
  assert.equal(JalaliCalendar.parseKey('1404/12/30'), null);
  assert.equal(JalaliCalendar.parseKey('abc'), null);
});

test('adding days and months crosses boundaries', () => {
  assert.deepEqual(JalaliCalendar.addDays({ year: 1404, month: 12, day: 29 }, 1), { year: 1405, month: 1, day: 1 });
  assert.deepEqual(JalaliCalendar.addMonths({ year: 1405, month: 12 }, 1), { year: 1406, month: 1 });
  assert.deepEqual(JalaliCalendar.addMonths({ year: 1405, month: 1 }, -1), { year: 1404, month: 12 });
  assert.equal(JalaliCalendar.daysBetween({ year: 1405, month: 1, day: 1 }, { year: 1405, month: 1, day: 11 }), 10);
});
