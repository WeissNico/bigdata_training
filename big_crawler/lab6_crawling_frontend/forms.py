"""In this module we define some standard forms using Flask-WTF forms.

These work in a dynamic way.
Author: Johannes Mueller <j.mueller@reply.de
"""
from flask_wtf import FlaskForm
from wtforms.widgets import html_params
import wtforms.widgets as widgets
from wtforms.fields import SubmitField, SelectMultipleField
from wtforms.fields.html5 import DecimalRangeField, DateField, SearchField
from wtforms.validators import Optional


class MultipleOptionsField(SelectMultipleField):
    """Create an input field for a multi-checkbox list.

    This behaves like a SelectMultipleField and therefore inherits it.
    Ripped from:
        https://wtforms.readthedocs.io/en/stable/widgets.html#custom-widgets .
    """
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()


def multi_checkbox_widget(field,
                          ul_class="multi-check",
                          li_class="",
                          badge_class="badge badge-secondary",
                          label_class="form-check-label",
                          text_class="overflow-ellipsis",
                          **kwargs):
    """A widget for displaying a multiple-select with checkboxes"""

    kwargs.setdefault("type", "checkbox")
    field_id = kwargs.pop("id", field.id)
    html = ["<ul {}>".format(html_params(id=field_id, class_=ul_class))]
    for (value, count), label, checked in field.iter_choices():
        choice_id = f"{field_id}-{value}"
        options = dict(kwargs, name=field.name,
                       value=value, id=choice_id)
        if checked:
            options["checked"] = "checked"
        html.append("<li {}>".format(html_params(class_=li_class)))
        html.append("<input {}/>".format(html_params(**options)))
        html.append("<label {}>".format(html_params(for_=choice_id,
                                                    class_=label_class)))
        html.append("<span {}>{}</span>".format(
            html_params(class_=badge_class),
            count))
        html.append("<span {}>{}</span>".format(
            html_params(class_=text_class),
            label))
    html.append("</label>\n</li>\n</ul>")
    return "\n".join(html)


def filter_form_factory(filters):
    """Takes the aggregation from the search results and constructs a form.

    Args:
        filters (dict): the filters as constructed in elastic_transforms.

    Returns

    """
    class FilterForm(FlaskForm):
        """The form for displaying the filter options in the searchbar.

        Normally not all the fields will be rendered.
        """
        q = SearchField("Search", [Optional()])
        submit = SubmitField("Search")

    # create the form and fill it with the appropriate filter values
    for key, value in filters.items():
        if key == "date":
            FilterForm.date_from = DateField(
                "from",
                [Optional()],
                default=value["from"]
            )
            FilterForm.date_to = DateField(
                "to",
                [Optional()],
                default=value["to"]
            )
        elif "from" in value:
            setattr(FilterForm, f"{key}_from", DecimalRangeField(
                "from",
                [Optional()],
                default=value["from"])
            )
            setattr(FilterForm, f"{key}_to", DecimalRangeField(
                "to",
                [Optional()],
                default=value["to"])
            )
        else:
            setattr(FilterForm, key, SelectMultipleField(
                key.title(),
                widget=multi_checkbox_widget,
                choices=[((f["value"], f["count"]), f["value"])
                         for f in value]))
    return FilterForm
