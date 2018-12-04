// This module provides some general functionality regarding lists.
// It uses mithril.js.
// Author: Johannes Müller

// Create a model for the items in the list
const ListContent = {
    fromElement: function(element) {
        var itemString = element.getAttribute("data-items");
        var items = JSON.parse(itemString);
        return items || [];
    },
    sync: function(url, items) {
        return m.request({
            method: "PUT",
            url: url,
            data: items,
            withCredentials: true,
        })
    }
}

const makePair = (el) => {
    if (typeof el !== "string" && Array.isArray(el) && el.length > 1) {
        return {id: el[0], name: el[1]};
    }
    else if (el && (el.hasOwnProperty("id") || el.hasOwnProperty("name"))) {
        el.id = el.id || el.name;
        el.name = el.name || el.id;
        return el;
    }
    return {id: el, name:el};
}

const makePairs = (list) => {
    list = list || [];
    return list.map(makePair);
}

var FakeSelect = {
    oninit: (vnode) => {
        vnode.state.items = makePairs(vnode.attrs.items);
        vnode.state.default = vnode.attrs.value;
        if (!vnode.attrs.value) {
            let justValues = vnode.state.items.filter(item => {
                return item.id !== "###" && item.id !== "---";
            });
            vnode.state.default = (justValues.length > 0) && justValues[0];
        }
    },
    view: (vnode) => {
        return m(".fakeSelect", {
            id: vnode.attrs.name + "Select"
        }, [
            m("input[type='hidden']", {
                id: vnode.attrs.name + "Value",
                name: vnode.attrs.name,
                value: vnode.attrs.value || vnode.state.default
            }),
            m("button[type='button'].btn.btn-outline-secondary.btn-block.dropdown-toggle.overflow-ellipsis", {
                "data-toggle": "dropdown",
                "aria-expanded": false
            }, [
                m("span.sr-only", "Toggle selection dropdown"),
                // display the first name entry
                m("span", makePair(vnode.attrs.value).name || vnode.state.default.name)
            ]),
            m(".dropdown-menu dropdown-fake-select", 
                vnode.state.items.map(item => {
                    if (item.id === "###") {
                        return m("h6.dropdown-header", item.name)
                    }
                    else if (item.id === "---") {
                        return m(".dropdown-divider")
                    }
                    else {
                        return m("a.dropdown-item[href='#']", {
                            onclick: () => {
                                vnode.attrs.onselect(item);
                            }
                        },
                        item.name)
                    }
                })
            )
        ])
    }
}

var CheckBoxes = {
    // This component represents a dynamic array of checkboxes.
    view: (vnode) => {
        return m(".check-array", 
            vnode.attrs.values.map((el, idx) => {
                return m("label.badge-box.m-1", {
                    for: el.id + "Value",
                    key: el.name
                }, [
                    m("input[type='checkbox']", {
                        id: el.id + "Value",
                        name: "options",
                        value: el.id,
                        // checked has problems with 'undefined'
                        checked: el.active || false,
                        oninput: m.withAttr("checked", (checked) => {
                            el.active = checked;
                            vnode.attrs.oninput && vnode.attrs.oninput(checked);
                        })
                    }),
                    m("span.badge", el.name)
                ])
            })
        )
    }
}
                    

var EditListItem = {
    // This components represents a single item in a custom edit-list
    // which can be deleted
    view: (vnode) => {
        return m("li.list-group-item", [
            m("span.item-text", vnode.attrs.item.name),
            m("a.item-delete.text-danger.float-right", {
                href: "#",
                onclick: vnode.attrs.deleteItem
            },
                m("span.fas.fa-trash")
            )
        ]);
    }
}

var CheckListItem = {
    // This components represents a single item in a custom check-list
    // it provides a checkbox and a proper id.
    view: function (vnode) {
        return m("li.list-group-item", {
            class: vnode.attrs.item.active ? "active" : ""
        }, [
                m("label", { for: vnode.attrs.item.id }, [
                    m("input[type=checkbox]", {
                        id: vnode.attrs.item.id,
                        oninput: m.withAttr("checked", function (arg) {
                            vnode.attrs.item.active = arg;
                        }),
                        name: vnode.attrs.name,
                        value: vnode.attrs.item.value || vnode.attrs.item.id,
                        checked: vnode.attrs.item.active
                    }),
                    m("span.far", { 
                        class: vnode.attrs.item.active ? "fa-check-circle" : "fa-circle"
                    }),
                    m("span", " " + vnode.attrs.item.name)
                ])
        ]);
    }
}

var BlankList = {
    oninit: function(vnode) { 
        vnode.state.items = vnode.attrs.items;
    },
    view: function(vnode) {
        let itemComponent = vnode.attrs.kind || EditListItem;
        return m("div", {
            class: vnode.attrs.class,
            id: vnode.attrs.name
        }, [
            m("ul.list-group",
                vnode.state.items.map(function(item, idx) {
                    return m(itemComponent, {
                        key: item.id,
                        item: item,
                        name: vnode.attrs.name,
                        deleteItem: function() {
                            vnode.state.items.splice(idx, 1);
                        }
                    });
                })
            )
        ]);
    }
}

var CheckList = {
    oninit: function(vnode) { 
        vnode.state.items = ListContent.fromElement(vnode.attrs.element);
    },
    view: function(vnode) {
        return m(BlankList, {
            class: "custom-check-list",
            items: vnode.state.items,
            kind: CheckListItem,
            name: vnode.attrs.name
        });
    }
}

var ItemEntry = {
    oninit: function(vnode) {
        vnode.state.newItem = null;
    },
    view: function(vnode) {
        return m(".btn-group.btn-block.my-2", [
            m("input[type='text'].item-input.form-control", {
                name: "newItem",
                placeholder: "new item name",
                oninput: m.withAttr("value", (v) => vnode.state.newItem = v)
            }),
            m("a.item-add.btn.btn-success", {
                name: "addNewItem",
                href: "#",
                onclick: () => vnode.attrs.items.push({
                    id: "",
                    name: vnode.state.newItem,
                })
            },
                m("span.fas.fa-plus")
            )
        ])
    }
}

var EditList = {
    oninit: function(vnode) { 
        vnode.state.items = ListContent.fromElement(vnode.attrs.element);
    },
    view: function(vnode) {
        let entry = vnode.attrs.entryComponent || ItemEntry;
        return [
            m(entry, {
                items: vnode.state.items,
            }),
            m(BlankList, {
                class: "editable-list",
                items: vnode.state.items,
                kind: EditListItem,
                name: vnode.attrs.name
            })
        ];
    }
}

var ModalToggler = {
    view: function(vnode) {
        return m("button.btn.btn-outline-primary.btn-block", {
            "type": "button",
            "data-toggle": "modal",
            "data-target": vnode.attrs.target
        }, vnode.attrs.children || [
            m("span.fas.fa-plus-circle"),
            m("span", " Add custom")
        ]);
    }
}

var ModalWrapper = {
    view: function(vnode) {
        const modalId = vnode.attrs.id;
        const labelId = vnode.attrs.id + "Label";
        return m(".modal.fade", {
            id: modalId,
            tabindex: -1,
            role: "dialog",
            "aria-labelledby": labelId,
            "aria-hidden": true
        }, [
            m(".modal-dialog[role='document']", [
                m(".modal-content", [
                    m(".modal-header", [
                        m("h5.modal-title", {id: labelId}, vnode.attrs.title),
                        m("button.close[type='button']", {
                            "data-dismiss": "modal",
                            "aria-label": "Close dialog"
                        }, 
                            m("span", {"aria-hidden": true}, 
                                m("span.far.fa-times-circle")
                            )
                        )
                    ]),
                    m(".modal-body", vnode.attrs.body),
                    m(".modal-footer", vnode.attrs.footer)
                ])
            ])
        ]);
    }
}