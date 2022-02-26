const api_prefix = "/api/v1.0";


Vue.directive("tooltip", function(el, binding){
    $(el).tooltip({
        title: binding.value,
        placement: binding.arg,
        trigger: 'hover'
    });
});


Vue.component("tab-content", {
    template: `
    <div>
      <div v-show="title == $parent.active_tab">
        <slot></slot>
      </div>
    </div>
    `,
    props: {
        title: {type: String},
    },
    inject: ["tabs", "active_tab"],
    created: function(){
        "use strict";
        this.tabs.push(this);
    }
});


Vue.component("tab-container", {
    template: `
      <div>
          <ul class="nav nav-tabs">
            <li class="nav-item" v-for="tab in tabs">
              <a class="nav-link" href="#" v-on:click="set_tab(tab.title)" :class="{active:(tab.title==active_tab)}">
                {{ tab.title }}
              </a>
            </li>
          </ul>
          <div>
            <slot></slot>
          </div>
      </div>
    `,
    props: {
        active_tab: {type: String}
    },
    data: function(){
        'use strict';
        return {tabs: []};
    },
    methods: {
        set_tab: function(tab_name){
            this.active_tab = tab_name;
        }
    },
    provide: function(){
        "use strict";
        return {"tabs": this.tabs, "active_tab": this.active_tab};
    }
});


Vue.component("ambience-location-view", {
    template: `
    <div class="card shadow">
      <div class="card-header">
        <div class="row">
          <div class="col-md-10">
            <h3>In scan {{ location.scan_name }}</h3>
          </div>
          <div class="col-md-2 d-grid">
            <a class="btn btn-primary" :href="'/scans/' + location.scan_id" target="_blank">
            Open full scan report
            <i class="fa fa-scroll"></i>
            </a>
          </div>
        </div>
      </div>
    
      <ul class="list-group list-group-flush">
        <li class="list-group-item">
          Path: {{ location.metadata.normalized_path }}
        </li>
        <li class="list-group-item">
          Mimetype: {{ location.metadata.mime }}
        </li>
        <li class="list-group-item">
          MD5: {{ location.metadata.md5 }}
        </li>
      </ul>
    </div>
    `,
    props: {
        location: {type: Object}
    },
});


Vue.component("ambience-search", {
    template: `
    <div class="row">
      <div class="col-md-10">
        <input autofocus type="text" class="form-control" placeholder="Type to search..." v-model="query" v-on:keyup.enter="search" />
      </div>

      <div class="col-md-2">
        <button class="btn btn-outline-secondary form-control" v-on:click="search">
          <i class="fa fa-search"></i>
          Search
        </button>
      </div>
    
    <div class="col-md-12 p-4" v-if="error">
      <div class="alert alert-danger text-center">
      <h2>
        <i class="fa fa-bug"></i>
        {{ error }}
      </h2>
      </div>
    </div>
    
    <div class="col-sm-12 text-center p-4" v-if="searching">
      <h2><i class="fa fa-circle-o-notch fa-spin fa-fw"></i> Searching</h2>
    </div>
    
    <div class="col-md-12 p-4" v-if="empty">
      <div class="alert alert-primary text-center">
      <h2>
        No search results found, try adjusting your search terms
      </h2>
      </div>
    </div>
    
    <div class="col-md-12 p-4" v-if="wizard">
      <div class="card">
        <div class="card-header text-center">
          <h2>
            <i class="fa fa-brain"></i>
            What about some search tips?
          </h2>
        </div>
        <ul class="list-group list-group-flush">
          <li class="list-group-item">
            You can use the
            <mark>&</mark>, <mark>|</mark> and <mark>!</mark>
            operators in search terms for AND, OR and NOT conditions, for example: <mark>taint & eval & !return</mark>
          </li>
          <li class="list-group-item">
            Search terms containing spaces should be enclosed: <mark>"pickle exploit"</mark>
          </li>
          <li class="list-group-item">
            Search for <mark>password</mark> or <mark>token</mark> in detections
          </li>
          <li class="list-group-item">
            Search for <mark>setup.py</mark> in filepaths
          </li>
        </ul>
      </div>
    </div>

    <div class="col-lg-12 p-4" v-show="!(searching) && (detections || filepaths)">
        <tab-container :active_tab="'Detections'">
          <tab-content :title="'Detections'">
            <div class="row">
              <div class="col-md-12" v-if="detections && detections.length == 0">
                <div class="alert alert-primary text-center">
                  <h2>No detections found</h2>
                </div>
              </div>
            
              <div class="col-md-12 mt-2" v-for="d in detections">
                <detection :detection="d.detection">
                  <template v-slot:footer>
                    <hr />
                    <div class="row">
                      <div class="col-md-10">
                        <h3>In scan {{ d.scan_name }}</h3>
                      </div>
                      <div class="col-md-2 d-grid">
                        <a class="btn btn-primary" :href="'/scans/' + d.scan_id" target="_blank">
                        <i class="fa fa-file-medical-alt"></i>
                        Open full scan report
                        </a>
                      </div>
                    </div>
                  </template>
                </detection>
              </div>
            </div>
          </tab-content>
          <tab-content :title="'File paths'">
            <div class="row">
              <div class="col-md-12" v-if="filepaths && filepaths.length == 0">
                <div class="alert alert-primary text-center">
                  <h2>No file paths found</h2>
                </div>
              </div>
              <div class="col-md-12 mt-2" v-for="f in filepaths">
                <ambience-location-view :location="f"></ambience-location-view>
              </div>
            </div>
          </tab-content>
        </tab-container>
      </div>
    
    </div>
    `,
    data: function(){
        'use strict';
        return {
            query: "",
            search_type: "detections",
            detections: null,
            filepaths: null,
            error: null,
            wizard: true,
            searching: false,
            empty: false
        };
    },
    created: function(){
        var params = new URLSearchParams(window.location.search);
        const q = params.get("query");
        const s_type = params.get("search_type");

        if (!!s_type){
            this.search_type = s_type;
        }

        if (!!q){
            this.query = q;
            this.search();
        }
    },
    methods: {
        search: function() {
            'use strict';

            this.wizard = false;
            this.empty = false;
            this.searching = true;
            this.detections = null;
            this.filepaths = null;

            var t = this;
            axios.get(
                api_prefix + "/search",
                {params: {"q": this.query}}
            ).then(function(response){
                t.searching = false;

                if (!!response.data.error) {
                    t.error = response.data.error;
                    t.wizard = true;
                    return;
                }

                t.error = null;
                t.detections = response.data.detections;
                t.filepaths = response.data.filepaths;

            }).catch(function(error) {
                t.searching = false;
                t.error = "An error occured during the search";
            });
        }
    }
});

Vue.component("view-scan", {
    template: `
        <div class="row">
          <div class="col-sm-12 text-center p-4" v-if="!scan_data">
            <h2><i class="fa fa-circle-o-notch fa-spin fa-fw"></i> Loading scan</h2>
          </div>
          <div class="col-sm-12" v-if="!!scan_data">
            <tabs :results="scan_data"></tabs>
          </div>
        </div>
    `,
    props: {scan_id: {type: Number, required: true}},
    data: function(){
        'use strict';
        return {"scan_data": null};
    },
    methods: {
        fetch_scan: function() {
            var t = this;
            axios.get(
                api_prefix + "/scans/" + this.scan_id
            ).then(response => (t.scan_data = response.data));
        }
    },
    created: function(){
        if (this.scan_data === null) {
            this.fetch_scan();
        }
    }
});


Vue.component("latest-scans", {
    template: `
    <div class="card">
      <div class="card-header">

        <div class="tooltip bs-tooltip-top" role="tooltip">
  <div class="tooltip-arrow"></div>
      <div class="tooltip-inner">
        Some tooltip text!
      </div>
    </div>
        Latest scans
      </div>
      <div class="card-body d-grid gap-1">
        <div class="input-group input-group-sm" v-for="scan in scans">
          <span class="input-group-text form-control">
            {{ scan.name }}
          </span>
          <a :href="'/scans/'+scan.scan_id" class="btn btn-outline-primary" target="_blank"><i class="fa fa-file-medical-alt"></i></a>
          <a :href="'/project/'+scan.package" class="btn btn-outline-primary" target="_blank" v-if="scan.package"><i class="fa fa-box-open"></i></a>
        </div>
      </div>
    </div>
    `,
    data: function(){
        'use strict';
        return {scans: []};
    },
    methods: {
        truncate: function(str, len) {
            'use strict';
            len = len || 32;

            if (str.length < len) {
                return str;
            }

            return str.slice(0, len-4) + " ...";
        }
    },
    created: function(){
        var t = this;
        axios.get("/api/v1.0/latest_scans").then(response => (t.scans = response.data));
    }
});


Vue.component("ambience-stats", {
    template: `
    <div class="row">
      <div class="col-lg-6 mt-2" v-for="card in cards">
        <div class="card shadow">
          <div class="card-body text-center">
            <h4>
              <i class="fa fa-circle-o-notch fa-spin fa-fw" v-if="!data"></i>
              <span v-if="!!data">
                {{ data[card.cid] }}
              </span>
            </h4>
          </div>
          <div class="card-footer text-center">
            {{ card.label }}
          </div>
        </div>
      </div>
    </div>
    `,
    props: {
        cards: {type: Array, default: function(){return [
                {cid: "scans", label: "Scans"},
                {cid: "queue", label: "Scans in a queue"},
                {cid: "detections", label: "Detections"},
                {cid: "files", label: "Files scanned"},
                {cid: "size_human", label: "Data processed"}
            ]}},
        stats_interval: {type: Number, default: 60000}
    },
    data: function(){
        'use strict';
        return {data: null};
    },
    created: function(){
        this.load_stats();
    },
    methods: {
        load_stats: function(){
            var t = this;
            axios.get("/api/v1.0/stats").then(response => (t.data = response.data));
            if (this.stats_interval !== null && this.stats_interval > 0){
                setTimeout(this.load_stats, this.stats_interval);
            }
        }
    }
});


Vue.component("suspicious-packages", {
    template: `
    <div class="card">
      <div class="card-header">
        <h3>
          <i class="fa fa-box"></i>
          Most suspicious packages
          <i class="fa fa-circle-o-notch fa-spin fa-fw" v-if="!packages"></i>
        </h3>
      </div>
      
      <div class="card-body d-grid gap-1">
        <div class="input-group input-group-sm float-right" v-for="pkg in packages">
            <span class="input-group-text form-control">
              <span class="badge bg-danger rounded-pill">
                <i class="fa fa-trophy"></i>
                Score: {{ pkg.score }}
              </span> &nbsp;
              {{ pkg.name }}
            </span>
            <a class="btn btn-outline-primary" :href="'/scans/'+pkg.id" target="_blank">
              <i class="fa fa-file-medical-alt"></i>
              </a>
            <a class="btn btn-outline-primary" :href="'/project/'+pkg.package" target="_blank">
              <i class="fa fa-box-open"></i>
            </a>
          </div>
      </div>
    </div>
    `,
    //props: {packages: {type: Array, default: null}},
    data: (() => {return {packages: null}}),
    created: function(){
        var t = this;
        axios.get("/api/v1.0/suspicious_packages").then(response=>(t.packages=response.data));
    }
});


Vue.component("collapsible-card", {
    template: `
    <div class="card">
      <div class="card-header d-flex w-100 justify-content-between" v-on:click="toggle()" style="cursor: pointer">
        <span class="mb-1">
          <slot name="header" :slot_data="slot_data"></slot>
        </span>
        <span class="align-right">
          <i class="fa" :class="'fa-chevron-'+(obj[prop]?'left':'down')"></i>
        </span>
      </div>
      
      <div v-show="!obj[prop]">
        <slot :slot_data="slot_data"></slot>
      </div>
    </div>
    `,
    props: {
        obj: {type: Object, default: {}},
        prop: {type: String, default: "collapse"},
        slot_data: {type: Object, default: {}}
    },
    methods: {
        toggle: function(){
            'use strict';
            this.obj[this.prop] = !(this.obj[this.prop]);
        }
    }
});


Vue.component("package-browser", {
    template: `
    <div class="row">
      <div class="col-md-4 border rounded p-2">
        <div class="row">
          <div class="col-sm-12">
            <div class="input-group mb-3 d-flex">
              <button class="btn btn-primary" v-on:click="search()">
                  <i class="fa fa-search"></i>
                  Search
              </button>
              <button class="btn btn-danger">
                  <i class="fa fa-eraser"></i>
                  Reset filters
              </button>
            </div>
          </div>
        
          <!--div class="col-sm-12">
            <input class="form-control" type="text" placeholder="Filter name...">
          </div-->
        
          <div class="col-sm-12">
            <collapsible-card :obj="collapsed" :prop="'tags'" :slot_data="{filters: filters, tags: all_tags}">
              <template v-slot:header="slotProps">
                <i class="badge bg-secondary">{{ slotProps.slot_data.tags.length }}</i>
                Tags
              </template>
              <template v-slot:default="slotProps">
                <ul class="list-group">
                  <li v-for="tag in slotProps.slot_data.tags" class="list-group-item">
                    <input class="form-check-input me-1" type="checkbox" v-model="slotProps.slot_data.filters.tags[tag]">
                    {{ tag }}
                  </li>
                </ul>
              </template>
            </collapsible-card>
          </div>
          
          <div class="col-sm-12">
            <collapsible-card :obj="collapsed" :prop="'detection_types'" :slot_data="{filters: filters, dtypes: all_detection_types}">
              <template v-slot:header="slotProps">
                <i class="badge bg-secondary">{{ slotProps.slot_data.dtypes.length }}</i>
                Detection types
              </template>
              <template v-slot:default="slotProps">
                <ul class="list-group">
                  <li v-for="dtype in slotProps.slot_data.dtypes" class="list-group-item">
                    <input class="form-check-input me-1" type="checkbox" v-model="slotProps.slot_data.filters.detection_types[dtype]">
                    {{ dtype }}
                  </li>
                </ul>
              </template>
            </collapsible-card>
          </div>
          
          <div class="col-sm-12">
            <collapsible-card :obj="collapsed" :prop="'indicators'" :slot_data="{filters: filters, indicators: all_indicators}">
              <template v-slot:header="slotProps">
                <i class="badge bg-secondary">{{ slotProps.slot_data.indicators.length }}</i>
                Behavioral Indicators
              </template>
              <template v-slot:default="slotProps">
                <ul class="list-group">
                  <li v-for="i in slotProps.slot_data.indicators" class="list-group-item">
                    <input class="form-check-input me-1" type="checkbox" v-model="slotProps.slot_data.filters.indicators[i.id]">
                    {{ i.name }}
                  </li>
                </ul>
              </template>
            </collapsible-card>
          </div>
          
        </div>
      </div>
      <div class="col-md-8">
        <div class="card">
          <div class="card-header text-center">
            <h2>
              Results
            </h2>
          </div>
          
          <div class="card-body" >
            <div class="alert alert-warning text-center" v-if="(!!results) && results.count === 0">
              <h4>
                <i class="fa fa-filter"></i>
                We couldn't find the package you are looking for. Try adjusting the filter.
              </h4>
            </div>
            
            <div class="alert alert-secondary text-center" v-if="results === null">
              <h4>
                <i class="fa fa-arrow-left"></i>
                Select filters from the sidebar and then search for packages
              </h4>
            </div>
            
            <div v-if="!!results" class="d-grid gap-1 w-100">
                <div class="input-group input-group-sm" v-for="result in results.packages">
                  <span class="input-group-text form-control">
                    <span class="badge bg-secondary">Score: {{ result.score }}</span> &nbsp;
                    <i class="fa fa-box"></i> &nbsp;
                    {{ result.name }}
                  </span>
                  <a :href="'/project/' + result.package + '/' + result.release" class="btn btn-outline-secondary" target="_blank">
                    <i class="fa fa-box-open"></i>
                    Open package
                  </a>
                  <a :href="'/scans/'+result.id" class="btn btn-outline-secondary" target="_blank">
                    <i class="fa fa-file-medical-alt"></i>
                    Open scan report
                  </a>
                </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    `,
    props: {
        all_tags: {type: Array, default: []},
        all_detection_types: {type: Array, default: []},
        all_indicators: {type: Array, default: []},
        collapsed: {type: Object, default: {tags: true, detection_types: true, indicators: true}},
        filters: {type: Object, default: {tags: {}, detection_types: {}, indicators: {}}},
        results: {type: Object, default: null}
    },
    created: function(){
        var t = this;
        axios({
            url: "/graphql",
            method: "POST",
            data: {query:`{
                allTags(sort:TAG_ASC) {edges {node {tag}}},
                allBehavioralIndicators(sort:NAME_ASC) {edges {node {indicatorId, name}}},
                allDetectionTypes
            }`}
        }).then(function(response){
            var i = 0;
            var tags = [];
            var indicators = [];

            for (i=0; i < response.data.data.allTags.edges.length; i++){
                tags.push(response.data.data.allTags.edges[i].node.tag);
            }

            var i_data = response.data.data.allBehavioralIndicators.edges;

            for (i=0; i < i_data.length; i++){
                indicators.push({id: i_data[i].node.indicatorId, name: i_data[i].node.name});
            }

            t.all_tags = tags;
            t.all_detection_types = response.data.data.allDetectionTypes;
            t.all_indicators = indicators;
            //t.search();
        })
    },
    methods: {
        filterCheckbox: function(obj) {
            'use strict';
            var keys = [];

            for (var key in obj) {
                if (obj.hasOwnProperty(key) && obj[key] === true){
                    keys.push(key);
                }
            }

            return keys;
        },
        search: function(){
            var t = this;

            var q = {
                tags: this.filterCheckbox(this.filters.tags),
                detection_types: this.filterCheckbox(this.filters.detection_types),
                indicators: this.filterCheckbox(this.filters.indicators)
            };

            axios({
                url: "/packages/filter",
                method: "POST",
                data: q
            }).then(function(response){
                t.results = response.data;
            });
        }
    }
})

Vue.component("search-bar", {
    template: `
    <div class="d-flex">
        <input class="form-control me-2" type="search" placeholder="Search" v-model="query" v-on:keyup.enter="search">
    </div>
    `,
    methods: {
        search: function(){
            'use strict';
            if (!this.query){
                window.location.href = "/search";
            }

            window.location.href = "/search?query=" + encodeURIComponent(this.query);
        }
    },
    data: function(){
        'use strict'
        return {query: null}
    }
})


Vue.component("cron-job-log", {
    template: `
    <div class="card">
      <div class="card-header">
        Cron job log
      </div>
      <div class="card-body">
        <table class="table table-hover table-bordered table-sm">
          <thead>
            <tr>
              <th>Job ID</th>
              <th>Run ID</th>
              <th>Command</th>
              <th>Status</th>
              <th>Start time</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="l in log" :class='{"table-success": l.status === "succeeded", "table-danger": l.status === "failed", "table-info": l.status === "running"}'>
              <td>{{ l.jobid }}</td>
              <td>{{ l.runid }}</td>
              <td>{{ l.command }}</td>
              <td>{{ l.status }}</td>
              <td>{{ l.start_time }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    `,
    data: function(){
        'use strict';
        return {log: null};
    },
    created: function(){
        'use strict';
        this.refresh_log();
    },
    methods: {
        refresh_log: function(){
            'use strict';
            var t = this;
            axios.get("/api/v1.0/system/cron_log").then(function(response){
                t.log = response.data;
            });

            setTimeout(this.refresh_log, 3000);
        }
    }
});


Vue.component("running-scans", {
    template: `
      <table class="table table-sm table-hover table-bordered table-flex">
        <thead>
          <tr>
            <th>ID</th>
            <th>URI</th>
            <th>Runtime</th>
            <th>Updated</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="s in scans">
            <td>{{ s.queue_id }}</td>
            <td>{{ s.uri }}</td>
            <td>{{ s.runtime }}</td>
            <td>{{ s.updated }}</td>
          </tr>
        </tbody>
      </table>
    `,
    data: function(){
        'use strict';
        return {scans: []};
    },
    created: function(){ this.refresh_scans(); },
    methods: {
        refresh_scans: function(){
            'use strict';
            var t = this;
            axios.get("/api/v1.0/system/running_scans").then(function(response){
                t.scans = response.data;
            });

            setTimeout(this.refresh_scans, 1000);
        }
    }
});
