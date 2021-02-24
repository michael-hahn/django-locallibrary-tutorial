from django.shortcuts import render

# Create your views here.

from .models import Book, Author, BookInstance, Genre, SignUp

# from catalog.cache import NameAgeBst, NameDateBst, NameSortedList, AgeMinHeap, NameGPAHashTable
from catalog.forms import SignUpForm, RemoveForm
from django.splice.splicetypes import SpliceStr, SpliceInt


def index(request):
    """View function for home page of site."""
    # Generate counts of some of the main objects
    num_books = Book.objects.all().count()
    num_instances = BookInstance.objects.all().count()
    # Available copies of books
    num_instances_available = BookInstance.objects.filter(status__exact='a').count()
    num_authors = Author.objects.count()  # The 'all()' is implied by default.

    # Number of visits to this view, as counted in the session variable.
    num_visits = request.session.get('num_visits', 1)
    request.session['num_visits'] = num_visits+1

    # Render the HTML template index.html with the data in the context variable.
    return render(
        request,
        'index.html',
        context={'num_books': num_books, 'num_instances': num_instances,
                 'num_instances_available': num_instances_available, 'num_authors': num_authors,
                 'num_visits': num_visits},
    )


from django.views import generic


class BookListView(generic.ListView):
    """Generic class-based view for a list of books."""
    model = Book
    paginate_by = 10


class BookDetailView(generic.DetailView):
    """Generic class-based detail view for a book."""
    model = Book


class AuthorListView(generic.ListView):
    """Generic class-based list view for a list of authors."""
    model = Author
    paginate_by = 10


class AuthorDetailView(generic.DetailView):
    """Generic class-based detail view for an author."""
    model = Author


from django.contrib.auth.mixins import LoginRequiredMixin


class LoanedBooksByUserListView(LoginRequiredMixin, generic.ListView):
    """Generic class-based view listing books on loan to current user."""
    model = BookInstance
    template_name = 'catalog/bookinstance_list_borrowed_user.html'
    paginate_by = 10

    def get_queryset(self):
        return BookInstance.objects.filter(borrower=self.request.user).filter(status__exact='o').order_by('due_back')


# Added as part of challenge!
from django.contrib.auth.mixins import PermissionRequiredMixin


class LoanedBooksAllListView(PermissionRequiredMixin, generic.ListView):
    """Generic class-based view listing all books on loan. Only visible to users with can_mark_returned permission."""
    model = BookInstance
    permission_required = 'catalog.can_mark_returned'
    template_name = 'catalog/bookinstance_list_borrowed_all.html'
    paginate_by = 10

    def get_queryset(self):
        return BookInstance.objects.filter(status__exact='o').order_by('due_back')


from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect
from django.urls import reverse
import datetime
from django.contrib.auth.decorators import login_required, permission_required

# from .forms import RenewBookForm
from catalog.forms import RenewBookForm


@login_required
@permission_required('catalog.can_mark_returned', raise_exception=True)
def renew_book_librarian(request, pk):
    """View function for renewing a specific BookInstance by librarian."""
    book_instance = get_object_or_404(BookInstance, pk=pk)

    # If this is a POST request then process the Form data
    if request.method == 'POST':

        # Create a form instance and populate it with data from the request (binding):
        form = RenewBookForm(request.POST)

        # Check if the form is valid:
        if form.is_valid():
            # process the data in form.cleaned_data as required (here we just write it to the model due_back field)
            book_instance.due_back = form.cleaned_data['renewal_date']
            book_instance.save()

            # redirect to a new URL:
            return HttpResponseRedirect(reverse('all-borrowed'))

    # If this is a GET (or any other method) create the default form
    else:
        proposed_renewal_date = datetime.date.today() + datetime.timedelta(weeks=3)
        form = RenewBookForm(initial={'renewal_date': proposed_renewal_date})

    context = {
        'form': form,
        'book_instance': book_instance,
    }

    return render(request, 'catalog/book_renew_librarian.html', context)


def signup(request):
    """View function for user signup in the sign-up form."""
    # If this is a POST request then process the Form data
    if request.method == 'POST':
        # Create a form instance and populate it with data from the request (binding):
        form = SignUpForm(request.POST)

        # Check if the form is valid:
        if form.is_valid():
            # process the data in form.cleaned_data as required
            # bst = NameAgeBst(name=form.cleaned_data['name'],
            #                  age=form.cleaned_data['age'],
            #                  key="name")
            # bst.save()
            # bst = NameDateBst(name=form.cleaned_data['name'],
            #                   date=form.cleaned_data['date'],
            #                   key="name")
            # bst.save()
            # sl = NameSortedList(name=form.cleaned_data['name'])
            # sl.save()
            # mh = AgeMinHeap(age=form.cleaned_data['age'])
            # mh.save()
            # ht = NameGPAHashTable(name=form.cleaned_data['name'],
            #                       gpa=form.cleaned_data['gpa'],
            #                       key="name")
            # ht.save()
            sign_up_model = SignUp(name=SpliceStr(form.cleaned_data['name']),
                                   age=SpliceInt(form.cleaned_data['age']))

            sign_up_model.save()
            # redirect to a new URL:
            return HttpResponseRedirect(reverse('signup'))

    # If this is a GET (or any other method) create the default form
    else:
        form = SignUpForm()

    context = {
        'form': form,
    }

    return render(request, 'catalog/signup.html', context)


def signup_delete(request):
    """View function for user removing their name from the sign-up form."""
    pass
    # # If this is a POST request then process the Form data
    # if request.method == 'POST':
    #     # Create a form instance and populate it with data from the request (binding):
    #     form = RemoveForm(request.POST)
    #
    #     # Check if the form is valid:
    #     if form.is_valid():
    #         # process the data in form.cleaned_data as required
    #         name = form.cleaned_data['name']
    #         age = NameAgeBst.objects.get(name)
    #         NameAgeBst.objects.delete(name)
    #         NameDateBst.objects.delete(name)
    #         NameSortedList.objects.delete(name)
    #         # age_min_heap cannot perform deletion
    #         NameGPAHashTable.objects.delete(name)
    #
    #         # redirect to a new URL:
    #         return HttpResponseRedirect(reverse('signup'))
    #
    # # If this is a GET (or any other method) create the default form
    # else:
    #     form = RemoveForm()
    #
    # context = {
    #     'form': form,
    # }
    #
    # return render(request, 'catalog/signup_delete.html', context)


class SignupList(generic.ListView):
    """Generic class-based list view for a list of authors."""
    model = SignUp
    paginate_by = 10
    template_name = "catalog/signup_list.html"


def signup_list(request):
    pass
#     """View function for displaying users who have signed up."""
    # sign_ups = list()
    # for name, age in NameAgeBst.objects:
    #     if isinstance(name, UntrustedMixin):
    #         if not name.synthesized:
    #             name = name.to_trusted()
    #         else:
    #             # If name is synthesized, do not use
    #             continue
    #     # same goes for age
    #     if isinstance(age, UntrustedMixin):
    #         if age.synthesized:
    #             continue
    #         else:
    #             age = age.to_trusted()
    #     date = NameDateBst.objects.get(name)
    #     if isinstance(date, UntrustedMixin):
    #         if not date.synthesized:
    #             date = date.to_trusted()
    #         else:
    #             continue
    #     if name in NameGPAHashTable.objects:
    #         gpa = NameGPAHashTable.objects.get(name)
    #         if isinstance(gpa, UntrustedMixin):
    #             if not gpa.synthesized:
    #                 gpa = gpa.to_trusted()
    #             else:
    #                 continue
    #         sign_ups.append((name, age, gpa, date))
    #     else:
    #         sign_ups.append((name, age, None, date))
    #
    # sorted_names = NameSortedList.objects
    # trusted_sorted_names = []
    # for name in sorted_names:
    #     if isinstance(name, UntrustedMixin):
    #         if not name.synthesized:
    #             trusted_sorted_names.append(name.to_trusted())
    #     else:
    #         trusted_sorted_names.append(name)
    # youngest_age = None
    # while AgeMinHeap.objects:
    #     youngest_age = AgeMinHeap.objects.get()
    #     if isinstance(youngest_age, UntrustedMixin):
    #         if not youngest_age.synthesized:
    #             youngest_age = youngest_age.to_trusted()
    #             break
    #         else:
    #             youngest_age = None
    #             AgeMinHeap.objects.pop()
    #     else:
    #         break
    #
    # # Render the HTML template signup.html with the data in the context variable.
    # return render(
    #     request,
    #     'catalog/signup_list.html',
    #     context={'signups': sign_ups,
    #              'sorted_names': trusted_sorted_names,
    #              'youngest_age': youngest_age,
    #              },
    # )


from django.contrib import auth


def logout(request):
    user_name = request.user.username
    # try:
    #     i = NameSortedList.objects.find(user_name)
    #     NameSortedList.objects.synthesize(i)
    # except ValueError as e:
    #     pass
    #
    # NameAgeBst.objects.synthesize(user_name)
    # NameDateBst.objects.synthesize(user_name)
    # NameGPAHashTable.objects.synthesize(user_name)

    auth.logout(request)
    return render(request,
                  'registration/logged_out.html',
                  context={"name": user_name})


from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from .models import Author


class AuthorCreate(PermissionRequiredMixin, CreateView):
    model = Author
    fields = ['first_name', 'last_name', 'date_of_birth', 'date_of_death']
    initial = {'date_of_death': '11/06/2020'}
    permission_required = 'catalog.can_mark_returned'


class AuthorUpdate(PermissionRequiredMixin, UpdateView):
    model = Author
    fields = '__all__' # Not recommended (potential security issue if more fields added)
    permission_required = 'catalog.can_mark_returned'


class AuthorDelete(PermissionRequiredMixin, DeleteView):
    model = Author
    success_url = reverse_lazy('authors')
    permission_required = 'catalog.can_mark_returned'


# Classes created for the forms challenge
class BookCreate(PermissionRequiredMixin, CreateView):
    model = Book
    fields = ['title', 'author', 'summary', 'isbn', 'genre', 'language']
    permission_required = 'catalog.can_mark_returned'


class BookUpdate(PermissionRequiredMixin, UpdateView):
    model = Book
    fields = ['title', 'author', 'summary', 'isbn', 'genre', 'language']
    permission_required = 'catalog.can_mark_returned'


class BookDelete(PermissionRequiredMixin, DeleteView):
    model = Book
    success_url = reverse_lazy('books')
    permission_required = 'catalog.can_mark_returned'
