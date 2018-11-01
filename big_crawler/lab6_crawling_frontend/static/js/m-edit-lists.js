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

var EditListItem = {
    // This components represents a single item in a custom edit-list
    // which can be deleted
    view: function (vnode) {
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
                        value: vnode.attrs.item.id,
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
        }, [
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

function findComponents() {
    // Finds the mount points for the components in a page and updates them
    // accoringly.
    var elements = $$("[data-component]");
    elements.forEach(function(el) {
        // retrieve the component by name
        var component = this[el.getAttribute("data-component")] || CheckList;
        m.mount(el, {view: function () {return m(component, {
            element: el,
            name: el.getAttribute("data-name")
        })}});
    });
}