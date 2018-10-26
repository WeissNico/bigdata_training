// Defines some dynamic lists using mithril and all other behaviour connected
// with the search dialog.
// Author: Johannes Mueller <j.mueller@reply.de>

// A modal Dialog component using ModalWrapper for the input of a custom
// date-range.
var TimePeriodModal = {
    oninit: function(vnode) {
        // initialize the dates to today (first ten letters of ISO format).
        vnode.state.dateFrom = new Date().toISOString().slice(0, 10);
        vnode.state.dateTo = new Date().toISOString().slice(0, 10);
    },
    view: function(vnode) {
        return m(ModalWrapper, {
            id: vnode.attrs.id,
            title: vnode.attrs.title,
            body: m(".form-row", [
                m(".col-md-6.col-sm-12.form-group", [
                    m("label[for='dateFrom']", [
                        m("span.far.fa-calendar-alt"),
                        m("span", " Date from")
                    ]),
                    m("input[type='date'].form-control#dateFrom", {
                        value: vnode.state.dateFrom,
                        oninput: m.withAttr("value", function(val) {
                            vnode.state.dateFrom = val;
                        })
                    })
                ]),
                m(".col-md-6.col-sm-12.form-group", [
                    m("label[for='dateTo']", [
                        m("span.far.fa-calendar-alt"),
                        m("span", " Date to")
                    ]),
                    m("input[type='date'].form-control#dateTo", {
                        value: vnode.state.dateTo,
                        oninput: m.withAttr("value", function(val) {
                            vnode.state.dateTo = val;
                        })
                    })
                ])
            ]),
            footer: [
                m("button[type='button'].btn.btn-secondary", {
                    "data-dismiss": "modal"
                }, "Close"),
                m("button[type='button'].btn.btn-primary", {
                    onclick: function() {
                        vnode.attrs.items.push({
                            id: "tp_" + vnode.state.dateFrom + "_" + vnode.state.dateTo,
                            name: "From " + vnode.state.dateFrom + " to " + vnode.state.dateTo,
                            active: true
                        });
                        this.hide();
                    }
                },
                    "Add time period"
                )
            ]
        });
    }
}

// A modal-dialog component using ModalWrapper for the input of a new source.
var SourceModal = {
    oninit: function(vnode) {
        // initialize the states for the new resource
        vnode.state.sourceName = "",
        vnode.state.sourceUrl = "",
        vnode.state.sourceDescription = ""
    },
    view: function(vnode) {
        var formId = vnode.attrs.id + "Form";
        return m(ModalWrapper, {
            id: vnode.attrs.id,
            title: vnode.attrs.title,
            body: m("form", {id: formId},
                m(".form-row", [
                    m(".col-sm-12.form-group", [
                        m("label[for='sourceName']", [
                            m("span.fas.fa-list"),
                            m("span", " Name")
                        ]),
                        m("input[type='text'].form-control#sourceName", {
                            name: "name",
                            placeholder: "An Example Source",
                            value: vnode.state.sourceName,
                            oninput: m.withAttr("value", function(val) {
                                vnode.state.sourceName = val;
                            })
                        })
                    ]),
                    m(".col-sm-12.form-group", [
                        m("label[for='sourceUrl']", [
                            m("span.fas.fa-link"),
                            m("span", " URL")
                        ]),
                        m("input[type='url'].form-control#sourceUrl", {
                            name: "url",
                            placeholder: "http://example.com",
                            value: vnode.state.sourceUrl,
                            oninput: m.withAttr("value", function(val) {
                                vnode.state.sourceUrl = val;
                            })
                        })
                    ]),
                    m(".col-sm-12.form-group", [
                        m("label[for='sourceDescription']", [
                            m("span.fas.fa-font"),
                            m("span", " Description")
                        ]),
                        m("textarea.form-control#sourceDescription", {
                            name: "description",
                            rows: 4,
                            placeholder: "A short description of the resource",
                            value: vnode.state.sourceDescription,
                            oninput: m.withAttr("value", function(val) {
                                vnode.state.sourceDescription = val;
                            })
                        })
                    ])
                ])
            ),
            footer: [
                m("button[type='button'].btn.btn-secondary", {
                    "data-dismiss": "modal"
                }, "Close"),
                m("button[type='button'].btn.btn-primary", {
                    onclick: function() {
                        m.request({
                            method: "POST",
                            url: "/add_source",
                            data: vnode.state
                        })
                        .then(function(response) {
                            if (response.success) {
                                console.log("Success!");
                            }
                            vnode.attrs.items.push(response.source);
                            this.hide();
                        });
                    }
                },
                    "Add new source!"
                )
            ]
        });
    }
}

// a custom check-list for the time-periods, utilizing the modal-dialog.
var TimePeriodCheckList = {
    oninit: function(vnode) { 
        vnode.state.items = ListContent.fromElement(vnode.attrs.element);
    },
    view: function(vnode) {
        var modalId = "addPeriodsModal"
        return [
            m(BlankCheckList, {
                items: vnode.state.items,
                name: vnode.attrs.name
            }),
            m(ModalToggler, {
                target: "#" + modalId
            }),
            m(TimePeriodModal, {
                id: modalId,
                items: vnode.state.items,
                title: "Add Time Period"
            })
        ];
    }
}

// a custom check-list for the sources, utilizing the modal-dialog.
var SourceCheckList = {
    oninit: function(vnode) { 
        vnode.state.items = ListContent.fromElement(vnode.attrs.element);
    },
    view: function(vnode) {
        var modalId = "addSourceModal"
        return [
            m(BlankCheckList, {
                items: vnode.state.items,
                name: vnode.attrs.name
            }),
            m(ModalToggler, {
                target: "#" + modalId
            }),
            m(SourceModal, {
                id: modalId,
                items: vnode.state.items,
                title: "Add New Source"
            })
        ];
    }
}

// find the components
findComponents();