// Create a model for the items in the list
var ListContent = {
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

var CheckListItem = {
    // This components represents a single item in a checklist
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

var BlankCheckList = {
    oninit: function(vnode) { 
        vnode.state.items = vnode.attrs.items;
    },
    view: function(vnode) {
        return m(".custom-check-list", {
            id: vnode.attrs.name
        }, [
            m("ul.list-group",
                vnode.state.items.map(function(item) {
                    return m(CheckListItem, {key: item.id,
                                            item: item});
            }))
        ]);
    }
}

var CheckList = {
    oninit: function(vnode) { 
        vnode.state.items = ListContent.fromElement(vnode.attrs.element);
    },
    view: function(vnode) {
        return m(BlankCheckList, {
            items: vnode.state.items,
            name: vnode.attrs.name
        });
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
        var modalId = vnode.attrs.id;
        var labelId = vnode.attrs.id + "Label";
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