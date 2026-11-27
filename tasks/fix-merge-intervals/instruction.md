The file /app/app.py has a function merge_intervals(intervals) that takes a
list of [start, end] pairs and merges all overlapping intervals.

Rules:
- intervals that overlap OR touch (for example [1, 2] and [2, 3]) are merged
- the input can be in any order
- an interval can be completely inside another one
- return a new list of [start, end] lists, sorted by start
- do not change the input
- an empty input returns an empty list

The current version has several bugs. Fix it.
