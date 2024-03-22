# Python Exercises

This repository stores the source code for selected Python exercises completed as part of Harvard University courses CS50X and CS50P

## Finance

"Finance" is a flask application in which users can simulate buying and selling stocks: the website uses the Yahoo Finance API to pull live stock prices.

The exercise was part of the CS50X course (and so uses the CS50 library which implements a version of SQL Alchemy).


## Birthdays

"Birthdays" is a simple flask application which allows users to add and display a list of people's names and their birthdays to a webpage. The data is stored and retrieved from the the birthdays.db database.

The exercise was part of the CS50X course (and so uses the CS50 library which implements a version of SQL Alchemy).

## DNA

"DNA" is a program which identifies to whom a sequence of DNA belongs, based on a database of people and their corresponding dna information, and a corresponding sample of dna sequences (.txt files) for which to test against.

The program takes two command line arguments: a database .csv file of the people to check for, and a dna sequence in which to check.

An example usage is provided below: 

    python dna.py databases/large.csv sequences/1.txt

