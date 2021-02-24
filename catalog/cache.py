# """In-memory data structures."""
#
# from django import forms
# from django.splice.structs import Struct
#
# from django.splice.backends.bst import BaseBST
# from django.splice.backends.sortedlist import BaseSortedList
# from django.splice.backends.minheap import BaseMinHeap
# from django.splice.backends.hashtable import BaseHashTable
#
#
# class NameAgeBst(Struct):
#     name = forms.CharField()
#     age = forms.IntegerField()
#     struct = BaseBST()
#
#
# class NameDateBst(Struct):
#     name = forms.CharField()
#     date = forms.DateTimeField()
#     struct = BaseBST()
#
#
# class NameSortedList(Struct):
#     name = forms.CharField()
#     struct = BaseSortedList()
#
#
# class AgeMinHeap(Struct):
#     age = forms.IntegerField()
#     struct = BaseMinHeap()
#
#
# class NameGPAHashTable(Struct):
#     name = forms.CharField()
#     gpa = forms.FloatField()
#     struct = BaseHashTable()
