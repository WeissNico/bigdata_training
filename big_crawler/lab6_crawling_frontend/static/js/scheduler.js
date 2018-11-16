// This module defines the dynamic content for the schedulers display.
// It uses mithril.js.
// Author: Johannes Müller

var Schedule = {
    schedules: [],
    status: "current",
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
        Schedule.status = "refreshing";
        m.request({
            url: "/scheduler",
            method: "POST",
            headers: {"X-Requested-With": "XMLHttpRequest"},
            data: Schedule.schedules
        }).then((response) => {
            if (response.success) {
                Schedule.status = "current";
                Schedule.schedules = response.schedules;
            }
            else {
                Schedule.status = "changed";
            }
        });
    },
    reload: () => {
        Schedule.status = "refreshing";
        m.request({
            url: "/scheduler",
            method: "GET",
            headers: {"X-Requested-With": "XMLHttpRequest"},
        }).then((response) => {
            if (response.success) {
                Schedule.status = "current";
                Schedule.schedules = response.schedules;
            }
            else {
                Schedule.status = "changed";
            }
        });
    },
    run: (job) => {
        job.status = "running";
        m.request({
            url: "/scheduler/run/:id",
            method: "POST",
            headers: {"X-Requested-With": "XMLHttpRequest"},
            data: {id: job.id}
        }).then((response) => {
            if (response.success) {
                job.status = "done";
            }
            else {
                job.status = "failed";
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
            title: (Schedule.current && Schedule.current.name && Schedule.current.name.name) || vnode.attrs.title,
            body: m(".form-row", [
                m(".col-md-6.col-sm-12.form-group", [
                    m("Label[for='crawler']", [
                        m("span.fas.fa-book"),
                        m("span", " Source")
                    ]),
                    m(FakeSelect, {
                        name: "crawler",
                        value: Schedule.current.crawler,  
                        items: vnode.attrs.sources,
                        onselect: (val) => {
                            Schedule.current.crawler = val;
                            Schedule.status = "changed";
                        }
                    })
                ]),
                m(".col-md-6.col-sm-12.form-group", [
                    m("Label[for='schedule']", [
                        m("span.fas.fa-calendar"),
                        m("span", " Schedule")
                    ]),
                    m(FakeSelect, {
                        name: "schedule",
                        value: Schedule.current.schedule,
                        items: vnode.attrs.triggers,
                        onselect: (val) => {
                            Schedule.current.schedule = deepcopy(val);
                            Schedule.status = "changed";
                        }
                    }),
                    m(CheckBoxes, {
                        name: "scheduleOptions",
                        values: Schedule.current.schedule && Schedule.current.schedule.options || [],
                        oninput: () => Schedule.status = "changed"
                    })
                ])
            ]),
            footer: [
                m("button[type='button'].btn.btn-secondary", {
                    "data-dismiss": "modal"
                }, "Close"),
                m("button[type='button'].btn.btn-primary", {
                    onclick: () => {
                        Schedule.status = "changed";
                        if (Schedule.current.hasOwnProperty("id")) {
                            $("#" + vnode.attrs.id).modal("hide");
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
        return m("button.btn.btn-success.btn-block.mb-3", {
            type: "button",
            "data-toggle": "modal",
            "data-target": vnode.attrs.target,
            onclick: Schedule.newSchedule
        }, [
            m("span.fas.fa-plus-circle"),
            m("span", " New schedule")
        ]);
    }
}

var SubmitButton = {
    view: (vnode) => {
        return m("button.btn.btn-block.mb-3", {
            type: "button",
            class: (Schedule.status === "current")
                    ? "btn-outline-success"
                    : "btn-success",
            onclick: Schedule.sync
        }, [
            m("span.fas.fa-sync", {
                class: Schedule.status === "refreshing" && "fa-spin"
            }),
            m("span", " Synchronize changes")
        ]);
    }
}

var RevertButton = {
    view: (vnode) => {
        return m("button.btn.btn-block.mb-3", {
            type: "button",
            class: (Schedule.status === "current")
                    ? "btn-outline-secondary"
                    : "btn-secondary",
            onclick: Schedule.reload
        }, [
            m("span.fas.fa-undo-alt", {
                class: Schedule.status === "refreshing" && "fa-spin"
            }),
            m("span", " Revert changes")
        ]);
    }
}

var ScheduleTable = {
    oninit: vnode => {
        vnode.state.keys = vnode.attrs.keys;
        Schedule.schedules = vnode.attrs.jobs;
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
                                return m("td", job[item].name || job[item].id)
                            }
                            else if (item === "controls") {
                                return m("td", 
                                    m(".btn-group[role='group']", [
                                        m("button[type='button'].btn.btn-secondary", {
                                            title: "Run job immediately",
                                            disabled: job.hasOwnProperty("id")
                                                      ? false
                                                      : true,
                                            onclick: () => {
                                                Schedule.run(job);
                                            }
                                        },
                                            m("span.fas.fa-paper-plane", {
                                                class: job.status == "running"
                                                       && "fa-pulse"
                                            })
                                        ),
                                        m("button[type='button'].btn.btn-secondary", {
                                            title: "Edit job properties",
                                            onclick: () => {
                                                Schedule.current = job;
                                                $("#addSchedule").modal("show");
                                            }
                                        },
                                            m("span.fas.fa-edit")
                                        ),
                                        m("button[type='button'].btn.btn-secondary", {
                                            title: "Remove job from schedule",
                                            onclick: () => {
                                                Schedule.status = "changed";
                                                Schedule.schedules.splice(idx, 1);
                                            }
                                        },
                                            m("span.fas.fa-trash")
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