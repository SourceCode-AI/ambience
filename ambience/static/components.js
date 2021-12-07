const api_prefix = "/api/v1.0";


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
      <div class="col-md-8">
        <input autofocus type="text" class="form-control" placeholder="Type to search..." v-model="query" v-on:keyup.enter="search" />
      </div>

      <div class="col-md-2">
        <select class="form-select" v-model="search_type">
          <option value="detections">Full text (detections)</option>
          <option value="filepaths">File paths</option>
        </select>
      </div>

      <div class="col-md-2">
        <button class="btn btn-outline-secondary" v-on:click="search">Search</button>
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
      
      <div class="col-md-12">
        <div class="row" v-if="detections" v-if="search_type == 'detections'">
          <div class="col-md-16 mt-2" v-for="d in detections">
            <detection :detection="d.detection">
              <template v-slot:footer>
                <hr />
                <div class="row">
                  <div class="col-md-10">
                    <h3>In scan {{ d.scan_name }}</h3>
                  </div>
                  <div class="col-md-2 d-grid">
                    <a class="btn btn-primary" :href="'/scans/' + d.scan_id" target="_blank">
                    Open full scan report
                    <i class="fa fa-scroll"></i>
                    </a>
                  </div>
                </div>
              </template>
            </detection>
          </div>
        </div>
        
        <div class="row" v-if="filepaths !== null" v-if="search_type == 'filepaths'">
          <div class="col-md-12 mt-2" v-for="f in filepaths">
            <ambience-location-view :location="f"></ambience-location-view>
          </div>
        </div>
      </div>
    </div>
    `,
    props: {
        query: {type: String, default: ""},
        search_type: {type: String, default: "detections"},
        detections: {type: Object, default: null},
        filepaths: {type: Object, default: null},
        error: {type: String, default: null},
        wizard: {type: Boolean, default: true},
        searching: {type: Boolean, default: false},
        empty: {type: Boolean, default: false}
    },
    methods: {
        search: function() {
            this.wizard = false;
            this.empty = false;
            this.searching = true;
            this.detections = null;
            this.filepaths = null;

            var t = this;
            axios.get(
                api_prefix + "/search/"+this.search_type,
                {params: {"q": this.query}}
            ).then(function(response){
                t.searching = false;

                if (!!response.data.error) {
                    t.error = response.data.error;
                    t.wizard = true;
                    return
                }

                t.error = null;
                t.detections = response.data.detections;
                t.filepaths = response.data.filepaths;
                t.empty = (response.data.count === 0);

            }).catch(function(error) {
                t.searching = false;
                t.error = "An error occured during the search";
            })
        }
    }
});

Vue.component("view-scan", {
    template: `
        <div class="row">
          <div class="col-sm-12 text-center p-4" v-if="scan_data === null">
            <h2><i class="fa fa-circle-o-notch fa-spin fa-fw"></i> Loading scan</h2>
          </div>
          <div class="col-sm-12" v-if="scan_data !== null">
            <tabs :results="scan_data"></tabs>
          </div>
        </div>
    `,
    props: {
        scan_id: {type: Number},
        scan_data: {type: Object, default: null}
    },
    methods: {
        fetch_scan: function() {
            var t = this;
            axios.get(
                api_prefix + "/scans/" + this.scan_id
            ).then(response => (t.scan_data = response.data))
        }
    },
    created: function(){
        if (this.scan_data === null) {
            this.fetch_scan();
        }
    }
});
