/**
 * Shared Jalali (Persian) calendar helpers.
 *
 * Every page that needs a date picker uses this one file, so the calendar math
 * lives in a single place. The conversion algorithm is the well known
 * "jalaali-js" one (valid for Jalali years -61 .. 3177).
 *
 * A date is always a plain object: { year, month, day } in the Jalali calendar.
 */
(function (root) {
  'use strict';

  const MONTH_NAMES = ['فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور', 'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند'];
  // The Persian week starts on Saturday.
  const WEEKDAY_SHORT = ['ش', 'ی', 'د', 'س', 'چ', 'پ', 'ج'];
  const WEEKDAY_FULL = ['شنبه', 'یکشنبه', 'دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنجشنبه', 'جمعه'];
  const FRIDAY_INDEX = 6;

  // Years where the length of the Jalali leap cycle changes.
  const LEAP_BREAKS = [-61, 9, 38, 199, 426, 686, 756, 818, 1111, 1181, 1210, 1635, 2060, 2097, 2192, 2262, 2324, 2394, 2456, 3178];

  const div = (a, b) => Math.trunc(a / b);
  const mod = (a, b) => a - Math.trunc(a / b) * b;

  /** Leap information for a Jalali year: leap offset, matching Gregorian year, March day of Nowruz. */
  function jalaliCycle(jalaliYear) {
    const breakCount = LEAP_BREAKS.length;
    const gregorianYear = jalaliYear + 621;
    let leapJalali = -14;
    let previousBreak = LEAP_BREAKS[0];
    let jump = 0;

    if (jalaliYear < previousBreak || jalaliYear >= LEAP_BREAKS[breakCount - 1]) {
      throw new RangeError('Jalali year out of range: ' + jalaliYear);
    }
    for (let i = 1; i < breakCount; i += 1) {
      const currentBreak = LEAP_BREAKS[i];
      jump = currentBreak - previousBreak;
      if (jalaliYear < currentBreak) { break; }
      leapJalali += div(jump, 33) * 8 + div(mod(jump, 33), 4);
      previousBreak = currentBreak;
    }
    let yearsIntoCycle = jalaliYear - previousBreak;
    leapJalali += div(yearsIntoCycle, 33) * 8 + div(mod(yearsIntoCycle, 33) + 3, 4);
    if (mod(jump, 33) === 4 && jump - yearsIntoCycle === 4) { leapJalali += 1; }

    const leapGregorian = div(gregorianYear, 4) - div((div(gregorianYear, 100) + 1) * 3, 4) - 150;
    const marchDay = 20 + leapJalali - leapGregorian;
    if (jump - yearsIntoCycle < 6) {
      yearsIntoCycle = yearsIntoCycle - jump + div(jump + 4, 33) * 33;
    }
    let leap = mod(mod(yearsIntoCycle + 1, 33) - 1, 4);
    if (leap === -1) { leap = 4; }
    return { leap, gregorianYear, marchDay };
  }

  /** Gregorian date to Julian day number. */
  function gregorianToDayNumber(year, month, day) {
    let dayNumber = div((year + div(month - 8, 6) + 100100) * 1461, 4) + div(153 * mod(month + 9, 12) + 2, 5) + day - 34840408;
    dayNumber = dayNumber - div(div(year + 100100 + div(month - 8, 6), 100) * 3, 4) + 752;
    return dayNumber;
  }

  /** Julian day number to Gregorian date. */
  function dayNumberToGregorian(dayNumber) {
    let j = 4 * dayNumber + 139361631;
    j += div(div(4 * dayNumber + 183187720, 146097) * 3, 4) * 4 - 3908;
    const i = div(mod(j, 1461), 4) * 5 + 308;
    const day = div(mod(i, 153), 5) + 1;
    const month = mod(div(i, 153), 12) + 1;
    const year = div(j, 1461) - 100100 + div(8 - month, 6);
    return { year, month, day };
  }

  function jalaliToDayNumber(year, month, day) {
    const cycle = jalaliCycle(year);
    return gregorianToDayNumber(cycle.gregorianYear, 3, cycle.marchDay) + (month - 1) * 31 - div(month, 7) * (month - 7) + day - 1;
  }

  function dayNumberToJalali(dayNumber) {
    const gregorianYear = dayNumberToGregorian(dayNumber).year;
    let year = gregorianYear - 621;
    const cycle = jalaliCycle(year);
    const nowruzDayNumber = gregorianToDayNumber(gregorianYear, 3, cycle.marchDay);
    let offset = dayNumber - nowruzDayNumber;
    if (offset >= 0) {
      if (offset <= 185) {
        return { year, month: 1 + div(offset, 31), day: mod(offset, 31) + 1 };
      }
      offset -= 186;
    } else {
      year -= 1;
      offset += 179;
      if (cycle.leap === 1) { offset += 1; }
    }
    return { year, month: 7 + div(offset, 30), day: mod(offset, 30) + 1 };
  }

  class JalaliCalendar {
    /** Today in the Jalali calendar (uses the viewer's local date). */
    static today() {
      return JalaliCalendar.fromDate(new Date());
    }

    static fromDate(date) {
      const dayNumber = gregorianToDayNumber(date.getFullYear(), date.getMonth() + 1, date.getDate());
      return dayNumberToJalali(dayNumber);
    }

    /** Local Date at noon, so daylight saving shifts can never change the day. */
    static toDate(jalaliDate) {
      const g = dayNumberToGregorian(jalaliToDayNumber(jalaliDate.year, jalaliDate.month, jalaliDate.day));
      return new Date(g.year, g.month - 1, g.day, 12);
    }

    /** Gregorian ISO string (YYYY-MM-DD): the format the database stores. */
    static toIso(jalaliDate) {
      const g = dayNumberToGregorian(jalaliToDayNumber(jalaliDate.year, jalaliDate.month, jalaliDate.day));
      const pad = (n) => String(n).padStart(2, '0');
      return g.year + '-' + pad(g.month) + '-' + pad(g.day);
    }

    static isLeapYear(year) {
      return jalaliCycle(year).leap === 0;
    }

    static daysInMonth(year, month) {
      if (month <= 6) { return 31; }
      if (month <= 11) { return 30; }
      return JalaliCalendar.isLeapYear(year) ? 30 : 29;
    }

    /** 0 = Saturday ... 6 = Friday. */
    static weekdayIndex(jalaliDate) {
      return (JalaliCalendar.toDate(jalaliDate).getDay() + 1) % 7;
    }

    static weekdayName(jalaliDate) {
      return WEEKDAY_FULL[JalaliCalendar.weekdayIndex(jalaliDate)];
    }

    /** Negative, zero or positive, like Array.prototype.sort comparators. */
    static compare(a, b) {
      return (a.year - b.year) || (a.month - b.month) || (a.day - b.day);
    }

    static isSame(a, b) {
      return Boolean(a) && Boolean(b) && JalaliCalendar.compare(a, b) === 0;
    }

    static addDays(jalaliDate, amount) {
      const dayNumber = jalaliToDayNumber(jalaliDate.year, jalaliDate.month, jalaliDate.day);
      return dayNumberToJalali(dayNumber + amount);
    }

    /** Whole days from `from` to `to` (negative when `to` is earlier). */
    static daysBetween(from, to) {
      return jalaliToDayNumber(to.year, to.month, to.day) - jalaliToDayNumber(from.year, from.month, from.day);
    }

    /** Moves a { year, month } pair by a number of months (may be negative). */
    static addMonths(view, amount) {
      const index = view.year * 12 + (view.month - 1) + amount;
      return { year: div(index, 12), month: mod(index, 12) + 1 };
    }

    /** Replaces Latin digits with Persian ones (works on padded strings like "08" too). */
    static toPersianDigits(value) {
      return String(value).replace(/[0-9]/g, (digit) => '۰۱۲۳۴۵۶۷۸۹'[Number(digit)]);
    }

    /** "۱۴۰۵/۰۸/۰۴" */
    static formatNumeric(jalaliDate) {
      return JalaliCalendar.toPersianDigits(JalaliCalendar.toKey(jalaliDate));
    }

    /** "سه‌شنبه، ۴ آبان" */
    static formatLong(jalaliDate) {
      return JalaliCalendar.weekdayName(jalaliDate) + '، ' + JalaliCalendar.toPersianDigits(jalaliDate.day) + ' ' + MONTH_NAMES[jalaliDate.month - 1];
    }

    /** "1405/08/04" with Latin digits, used for storage inside forms. */
    static toKey(jalaliDate) {
      const pad = (n) => String(n).padStart(2, '0');
      return jalaliDate.year + '/' + pad(jalaliDate.month) + '/' + pad(jalaliDate.day);
    }

    /** Parses "1405/08/04" (Latin or Persian digits). Returns null when invalid. */
    static parseKey(text) {
      const latin = String(text).replace(/[۰-۹]/g, (c) => String(c.charCodeAt(0) - 1776));
      const parts = latin.split('/').map(Number);
      if (parts.length !== 3 || parts.some((n) => !Number.isInteger(n))) { return null; }
      const [year, month, day] = parts;
      if (month < 1 || month > 12 || day < 1 || day > JalaliCalendar.daysInMonth(year, month)) { return null; }
      return { year, month, day };
    }

    /**
     * Everything a template needs to draw one month of the picker.
     *
     * options.year / options.month : the month on screen
     * options.selected             : the chosen date or null
     * options.min / options.max    : first and last selectable day (both optional)
     * options.isClosed(date)       : optional, true for days the restaurant is closed
     */
    static monthView(options) {
      const { year, month, selected = null, min = null, max = null, isClosed = null } = options;
      const today = JalaliCalendar.today();
      const firstDay = { year, month, day: 1 };
      const leadingBlanks = JalaliCalendar.weekdayIndex(firstDay);
      const dayCount = JalaliCalendar.daysInMonth(year, month);

      const cells = [];
      for (let i = 0; i < leadingBlanks; i += 1) {
        cells.push({ kind: 'blank' });
      }
      for (let day = 1; day <= dayCount; day += 1) {
        const date = { year, month, day };
        const isOff = Boolean((min && JalaliCalendar.compare(date, min) < 0) ||
          (max && JalaliCalendar.compare(date, max) > 0) ||
          (isClosed && isClosed(date)));
        cells.push({
          kind: 'day',
          date,
          label: JalaliCalendar.toPersianDigits(day),
          isOff,
          isToday: JalaliCalendar.isSame(date, today),
          isSelected: JalaliCalendar.isSame(date, selected),
          isFriday: JalaliCalendar.weekdayIndex(date) === FRIDAY_INDEX,
          aria: JalaliCalendar.formatLong(date)
        });
      }

      const previous = JalaliCalendar.addMonths({ year, month }, -1);
      const next = JalaliCalendar.addMonths({ year, month }, 1);
      const lastOfPrevious = { year: previous.year, month: previous.month, day: JalaliCalendar.daysInMonth(previous.year, previous.month) };
      const firstOfNext = { year: next.year, month: next.month, day: 1 };

      return {
        title: MONTH_NAMES[month - 1] + ' ' + JalaliCalendar.toPersianDigits(year),
        weekdays: WEEKDAY_SHORT,
        cells,
        previous,
        next,
        hasPrevious: !min || JalaliCalendar.compare(lastOfPrevious, min) >= 0,
        hasNext: !max || JalaliCalendar.compare(firstOfNext, max) <= 0
      };
    }
  }

  /**
   * Turns a month view into the flat data the picker template reads
   * (the template itself is the .dp markup that every page repeats).
   */
  class DatePickerView {
    /**
     * options.view           : { year, month } shown now
     * options.selected/min/max/isClosed : same meaning as JalaliCalendar.monthView
     * options.hint           : short legend text under the grid
     * options.onPick(date)   : called with the chosen Jalali date
     * options.onChangeView(v): called with the new { year, month }
     */
    static build(options) {
      const { view, onPick, onChangeView, hint = '' } = options;
      const month = JalaliCalendar.monthView({
        year: view.year, month: view.month,
        selected: options.selected, min: options.min, max: options.max, isClosed: options.isClosed
      });
      const todayView = JalaliCalendar.today();

      const cells = month.cells.map((cell) => {
        if (cell.kind === 'blank') {
          return { isBlank: true, isOn: false, isOffCell: false };
        }
        const classes = ['dp__day'];
        if (cell.isFriday) { classes.push('dp__day--friday'); }
        if (cell.isToday) { classes.push('dp__day--today'); }
        if (cell.isSelected) { classes.push('dp__day--selected'); }
        return {
          isBlank: false,
          isOn: !cell.isOff,
          isOffCell: cell.isOff,
          label: cell.label,
          aria: cell.aria,
          pressed: cell.isSelected,
          cls: classes.slice(1).join(' '),
          pick: () => onPick(cell.date)
        };
      });

      return {
        title: month.title,
        weekdays: month.weekdays,
        cells,
        hint,
        hasPrevious: month.hasPrevious,
        noPrevious: !month.hasPrevious,
        hasNext: month.hasNext,
        noNext: !month.hasNext,
        goPrevious: () => onChangeView(month.previous),
        goNext: () => onChangeView(month.next),
        goCurrentMonth: () => onChangeView({ year: todayView.year, month: todayView.month })
      };
    }
  }

  root.JalaliCalendar = JalaliCalendar;
  root.DatePickerView = DatePickerView;
}(typeof window !== 'undefined' ? window : globalThis));
