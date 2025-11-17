***************
Getting started
***************

``TextGrid Explorer`` is a desktop application for editing text in multiple
TextGrid files.


Installation
============


Basic operations
================

Importing TextGrid files
------------------------

The TextGrid Explorer builds a table from multiple TextGrid files.
In this table, the tiers form the columns and the intervals form the rows.

There are several methods you can use to convert your TextGrid files into
a TextGrid Table.

Method 1: Synchronized Intervals

In this method, the user selects one primary tier and one or more secondary tiers.

#. All the non-empty intervals in the primary tier will be shown as rows in the table.

#. If a secondary tier is selected, the application will find all non-empty intervals in that tier that share the exact same starting and ending times as an interval in the primary tier.

#. The text from these matching secondary intervals will then be displayed in the corresponding row and column.
