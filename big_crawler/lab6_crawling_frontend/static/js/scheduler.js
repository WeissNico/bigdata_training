// This module defines the dynamic content for the schedulers display.
// It uses mithril.js.
// Author: Johannes Müller

var Schedule = {
    schedules: [],
    current: {},
    newSchedule: () => {
        Schedule.current = {
            crawler: null,
            schedule: null
        };
    },
    fromElement: (el) => {
        Schedule.schedules = JSON.parse(el.getAttribute("data-schedules"));
    },
    sync: (data) => {
        m.request({
            url: "/scheduler/sync",
            method: "POST",
            data: Schedule.schedules
        }).then((response) => {
            if (response.success) {
                Schedule.schedules = response.schedules;
            }
        });
    }
}

// A modal Dialog component using ModalWrapper for the input of a new
// schedule.
var ScheduleModal = {
    view: (vnode) => {
        return m(ModalWrapper, {
            id: vnode.attrs.id,
            title: vnode.attrs.title,
            body: m(".form-row", [
                m(".col-md-4.col-sm-12.form-group", [
                    m("Label[for='crawler']", [
                        m("span.fas.fa-book"),
                        m("span", " Source")
                    ]),
                    m(FakeSelect, {
                        name: "crawler",
                        value: Schedule.current.crawler,  
                        items: vnode.attrs.sources,
                        onselect: (val) => Schedule.current.crawler = val[0]
                    })
                ])
            ]),
            footer: [
                m("button[type='button'].btn.btn-secondary", {
                    "data-dismiss": "modal"
                }, "Close"),
                m("button[type='button'].btn.btn-primary", {
                    onclick: () => {
                        if (Schedule.current.hasOwnProperty("_id")) {
                            p("editing");
                        }
                        else {
                            Schedule.schedules.push(Schedule.current);
                            $("#" + vnode.attrs.id).modal("hide");
                        }
                    }
                },
                    "Save"
                )
            ]
        });
    }
}

var ScheduleModalToggler = {
    view: (vnode) => {
        return m("button.btn.btn-success.btn-block", {
            "type": "button",
            "data-toggle": "modal",
            "data-target": vnode.attrs.target,
            onclick: Schedule.newSchedule
        }, [
            m("span.fas.fa-plus-circle"),
            m("span", " New schedule")
        ]);
    }
}

var ScheduleTable = {
    oninit: vnode => {
        vnode.state.keys = vnode.attrs.keys;
    },
    view: vnode => {
        return m("table.schedules.table.table-hover.table-responsive-lg", [
            m("thead", 
                vnode.state.keys.map(x => {
                    return m("th[scope='col']", toTitleCase(x));
                })
            ),
            m("tbody", [
                Schedule.schedules.map((job, idx) => {
                    return m("tr", 
                        vnode.state.keys.map(item => {
                            if (job.hasOwnProperty(item)) {
                                return m("td", job[item]);
                            }
                            else if (item === "controls") {
                                return m("td", 
                                    m(".btn-group[role='group']", [
                                        m("button[type='button'].btn.btn-secondary", {
                                            onclick: () => {
                                                Schedule.schedules.splice(idx, 1);
                                            }
                                        },
                                            m("span.fas.fa-trash")
                                        ),
                                        m("button[type='button'].btn.btn-secondary", {
                                            onclick: () => {
                                                Schedule.current = job;
                                                $("#addSchedule").modal("show");
                                            }
                                        },
                                            m("span.fas.fa-edit")
                                        )
                                    ])
                                );
                            }
                            else {
                                return m("td")
                            }
                        })
                    );
                })
            ])
        ]);
    }
}


findComponents();