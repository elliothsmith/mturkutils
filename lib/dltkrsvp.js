/*!
 * dicarlo lab javascript toolkit
 */
(function (dltk /*, window -- commented as unused */) {
    // Some shortcut references to dltk.js
    var defined = dltk.defined;
    var callable = dltk.callable;

    // Main
    dltk.RSVPModule = function RSVPModule($, optdct) {
        /**********************************************************************
         This is a module class that provides the "standard" RSVP
         sample-and-test experimental paradigm. This uses the new dltk graphics
         framework and delivers much more precise presentation time control.
         As a module, this is designed to be used with dltk.Experiment; i.e.,
         not to be used called directly by the user.

         Parameters:
         - $: the "sanitized" jquery object provided by the Experiment object
         - optdct: dictionary that contains options for this RSVP module.
           See ``OPTDCT_DEFAULT`` below for deails.
           (Better documentation TBD)

         Note: storing any other part of the calling Experiment object is
         discouraged because it can result in difficult-to-manage code.
         **********************************************************************/

        // -- Default constants
        var MSG_TRIAL_PROGRESS = 'Progress:<br /> ${CURRENT} of ${TOTAL}';
        var IMG_FIXATION = 'https://s3.amazonaws.com/task_images/fixation_360x360.png';
        var IMG_BLANK = 'https://s3.amazonaws.com/task_images/blank_360x360.png';
        var default_onUpdatePreloadProgress = function (argdct) {
            var progress = argdct.progress, total = argdct.total;
            var msg = "<font color=red style=background-color:white><b>Processing resources: " + 
                progress + "/" + total + "</b></font>";
            argdct.msg = msg;
        };

        var OPTDCT_DEFAULT = {
            /******* basic setup vars **********/
            elemSample: null, elemTest: null,   // html elems that fully contain sample and test stuffs respectively
            elemSampleCanvasID: null,  // canvas id to which the RSVP stimuli will be painted on. do not prepend #
            elemTestCanvasIDs: null,   // canvas ids for ans choices. must match the shape of imgFiles[0]. no #
            elemTestClickables: null,  // elements that will be made clickable to receive answers
            elemTrialCounter: null,
            imgFiles: null,
            ISIs: null,                // list of ISIs for trials
            stimdurations: null,       // list of stimdurations for trials
            /******** hook functions: these MUST be short to run (ideally less than 2ms) ***********/
            onUpdatePreloadProgress: default_onUpdatePreloadProgress,
            // all of the following onPreXXX, onPostXXX functions MUST be short to execute (ideally less than few ms)
            onPreISI1: null,
            onPostISI1: null,
            onPreStim: null,
            onPostStim: null,
            onPreISI2: null,
            onPosISI2: null,
            onPreDrawResponse: null,
            onPostDrawResponse: null,
            onResponseReady: null,
            onClickedTestBtn: null,
            /******** other options ***********/
            stopClockBeforeSample: true,
            startClockAfterSample: true,
            optdctQueueTrial: {},      // options to be passed to dltk.queueTrial(), except rsrcs -- see init()
            /******** text constants **********/
            msgTrialProgress: MSG_TRIAL_PROGRESS,
            imgFixation: IMG_FIXATION,
            imgBlank: IMG_BLANK,
        };

        // -- Private variables
        var o = dltk.applyDefaults(optdct, OPTDCT_DEFAULT);
        var that = this;
        var ctx_sample_on;
        var ctxs_test_on = [];
        var rsrcs = {};       // preloaded resources goes to here, not to the dltk.preloaded_rsrcs
        var primed = false;

        // -- Public variables
        this.totalTrials = null;
        this.trialNumber = null;

        // -- Private methods
        var _callHookfunctions = function _callHookfunctions(name, argdct) {
            if (callable(o[name])) o[name](argdct);
        };

        var _preISI1 = function _preISI1() {
            $(o.elemTest).hide();
            $(o.elemSample).show();
            // window.scrollTo(0, 0); // this causes suboptimal performance (forced sync)
            _callHookfunctions('onPreISI1');
        };
        var _postISI1 = function _postISI1() { _callHookfunctions('onPostISI1'); };
        var _preStim = function _preStim() { _callHookfunctions('onPreStim'); };
        var _postStim = function _postStim() { _callHookfunctions('onPostStim'); };
        var _preISI2 = function _preISI2() { _callHookfunctions('onPreISI2'); };
        var _postISI2 = function _postISI2() { _callHookfunctions('onPostISI2'); };
        var _preDrawResponse = function _preDrawResponse() {
            var msg = o.msgTrialProgress;
            msg = msg.replace('${CURRENT}', String(that.trialNumber + 1));
            msg = msg.replace('${TOTAL}', String(that.totalTrials));
            $(o.elemTrialCounter).html(msg);
            $(o.elemTest).show();
            $(o.elemSample).hide();
            _callHookfunctions('onPreDrawResponse');
        };
        var _postDrawResponse = function _postDrawResponse() { _callHookfunctions('onPostDrawResponse'); };

        var _runTrialOnce = function _runTrialOnce(argdct) {
            // Run single trial by using the new framework
            var trial_specs = [];
            var imgFiles = o.imgFiles;
            var trialNumber;

            if (that.trialNumber >= that.totalTrials) return;  // exceeded trials. abort.
            trialNumber = ++that.trialNumber;
            if (o.stopClockBeforeSample) argdct.stopClock();   // stop to minimize display burden

            // ISI 1 fixation dot
            trial_specs.push({
                urls: [o.imgFixation],
                contexts: [ctx_sample_on],
                duration: o.ISIs[trialNumber],
                pre: _preISI1,    // this MUST be short to run
                post: _postISI1   // this MUST be short to run
            });
            // sample stimulus
            trial_specs.push({
                urls: [imgFiles[trialNumber][0]],
                contexts: [ctx_sample_on],
                duration: o.stimdurations[trialNumber],
                pre: _preStim,    // this MUST be short to run
                post: _postStim   // this MUST be short to run
            });
            // ISI 2 blank
            trial_specs.push({
                urls: [o.imgBlank],
                contexts: [ctx_sample_on],
                duration: o.ISIs[trialNumber],
                pre: _preISI2,    // this MUST be short to run
                post: _postISI2   // this MUST be short to run
            });
            // response images
            trial_specs.push({
                urls: imgFiles[trialNumber][1],
                contexts: ctxs_test_on,
                duration: 0,              // immediately proceed to callback after paint
                pre: _preDrawResponse,    // this MUST be short to run
                post: _postDrawResponse   // this MUST be short to run
            });

            // Queue experiment
            dltk.queueTrial(trial_specs,
                function(hist, hist_delta, hist_delta_flush) {
                    // now response images are up
                    var trialStartTime = new Date();
                    setTimeout(function() {
                        // schedule all less time critical jobs later here
                        var t_spent = dltk.getTimeSpent(hist);
                        var t_ISI1 = dltk.round2(t_spent[1]);
                        var t_stim = dltk.round2(t_spent[2]);
                        var t_ISI2 = dltk.round2(t_spent[3]);
                        var hist_extract = dltk.getTimingHistoryExcerpt(hist, 'diff');
                        var hist_delta_extract = dltk.getTimingHistoryExcerpt(hist_delta, 'diffeach');

                        var argdct2 = {
                            t_ISI1: t_ISI1, t_stim: t_stim, t_ISI2: t_ISI2,
                            hist_extract: hist_extract, hist_delta_extract: hist_delta_extract,
                            hist: hist, hist_delta: hist_delta, hist_delta_flush: hist_delta_flush,
                            trialStartTime: trialStartTime
                        };

                        if (o.startClockAfterSample) argdct.startClock();
                        _callHookfunctions('onResponseReady', argdct2);

                        dltk.setDebugMessage('ISI1, stimon, ISI2 = ' +
                            String(t_ISI1) + ', ' + String(t_stim) + ', ' + String(t_ISI2));

                        argdct.finished();   // MUST call this to avoid experiment hang
                    }, 0);
                },
                o.optdctQueueTrial
            );
        };

        var _primeSystemAndRunTrialOnce = function _primeSystemAndRunTrialOnce(argdct) {
            // Prime the browser by running a single blank trial
            var trial_specs = [];

            if (o.stopClockBeforeSample) argdct.stopClock();   // stop to minimize display burden

            // blank
            trial_specs.push({
                urls: [o.imgBlank],
                contexts: [ctx_sample_on],
                duration: 50,
                pre: _preISI1,    // this MUST be short to run
                //post: _postISI1   // this MUST be short to run
            });
            // another blank
            trial_specs.push({
                urls: [o.imgBlank],
                contexts: [ctx_sample_on],
                duration: 50,
                //pre: _preStim,    // this MUST be short to run
                //post: _postStim   // this MUST be short to run
            });
            // yet another blank
            trial_specs.push({
                urls: [o.imgBlank],
                contexts: [ctx_sample_on],
                duration: 50,
                //pre: _preISI2,    // this MUST be short to run
                //post: _postISI2   // this MUST be short to run
            });

            // Queue experiment
            dltk.queueTrial(trial_specs,
                function() {
                    setTimeout(function() {
                        // by now, the system has been primed.  Proceed to actual experiment.
                        primed = true;
                        _runTrialOnce(argdct);
                        dltk.setDebugMessage('Primed.');
                    }, 0);
                },
                o.optdctQueueTrial
            );
        };

        var _safeRunTrialOnce = function _safeRunTrialOnce(argdct) {
            // This tries to ensure most optimal system performance by priming it when necessary
            if (!primed) _primeSystemAndRunTrialOnce(argdct);
            else _runTrialOnce(argdct);
        };

        var _clickedTestBtn = function _clickedTestBtn(index) {
            // Called when the turker clicks one of the test (answer) buttons
            var trialEndTime = new Date();
            var trialNumber = that.getCurrentTrialNumber();
            var trialInfo = that.getCurrentTrialInfo();
            var imgChosen = trialInfo.Sample[index];

            _callHookfunctions('onClickedTestBtn', 
                    {trialEndTime: trialEndTime, trialNumber: trialNumber,
                     trialInfo: trialInfo, imgChosen: imgChosen});
        };

        // -- Public methods
        this.init = function init() {
            // Initialize various RSVP related stuffs
            var arr, i;

            // imgFiles must be defined
            if (o.imgFiles === null || o.imgFiles.length === 0) {
                dltk.setDebugMessage('init: "imgFiles" is not defined.');
                return false;
            }
            // shape must match
            if (o.imgFiles[0][1].length != o.elemTestCanvasIDs.length ||
                    o.elemTestCanvasIDs.length != o.elemTestClickables.length) {
                dltk.setDebugMessage('init: "imgFiles[0][1]", "elemTestCanvasIDs", and "elemTestClickables" ' +
                        'have different shapes.');
                return false;
            }

            // on screen buffers for double buffering.
            // from: http://blog.bob.sh/2012/12/double-buffering-with-html-5-canvas.html
            ctx_sample_on = dltk.getOnScreenContextFromCanvas(o.elemSampleCanvasID);
            for (i = 0; i < o.elemTestCanvasIDs.length; i++)
                ctxs_test_on.push(dltk.getOnScreenContextFromCanvas(o.elemTestCanvasIDs[i]));

            that.totalTrials = o.imgFiles.length;
            that.trialNumber = -1;   // not yet started

            if (typeof(o.stimdurations) == 'number') {
                arr = [];
                for (i = 0; i < that.totalTrials; i++) arr.push(o.stimdurations);
                o.stimdurations = arr;
            }
            if (o.stimdurations.length != that.totalTrials) {
                dltk.setDebugMessage('init: The length of "stimdurations" is not equal to "totalTrials".');
                return false;
            }
            
            if (typeof(o.ISIs) == 'number') {
                arr = [];
                for (i = 0; i < that.totalTrials; i++) arr.push(o.ISIs);
                o.ISIs = arr;
            }
            if (o.ISIs.length != that.totalTrials) {
                dltk.setDebugMessage('init: The length of "ISIs" is not equal to "totalTrials".');
                return false;
            }

            $(o.elemSample).hide();
            $(o.elemTest).hide();
            o.optdctQueueTrial.rsrcs = rsrcs;
            return true;
        };

        this.getCurrentTrialInfo = function getCurrentTrialInfo() {
            // Returns the current info
            if (that.trialNumber < 0 || that.trialNumber >= that.totalTrials) return null;
            return {'Test': o.imgFiles[that.trialNumber][0], 'Sample': o.imgFiles[that.trialNumber][1]};
        };

        this.getCurrentTrialNumber = function getCurrentTrialNumber() {
            // Returns the current trial number
            return that.trialNumber;
        };

        this.setCurrentTrialNumber = function setCurrentTrialNumber(num) {
            if (num < -1 || num >= that.totalTrials) {   // -1 is fine; meaning expierment not yet started
                dltk.setDebugMessage('setCurrentTrialNumber: Invalid trialNumber');
                return false;
            }
            that.trialNumber = num;
            return true;
        };

        this.getTotalTrialNumber = function getTotalTrialNumber() {
            // Returns the current trial number
            return that.totalTrials;
        };

        this.onPreloadRsrcsAsync = function onPreloadRsrcsAsync(argdct) {
            // Preload resources.
            // This will be called when the system passes benchmark successfully by the Experiment object.
            // NOTE: This function MUST call argdct.finished() after loading all resources.  Otherwise,
            // the experiment will hang.

            // load fixation dot and blank image first...
            dltk.prepareResources(
                [[o.imgFixation, []], [o.imgBlank, []]], [ctx_sample_on, []],
                function() {
                    // ...then load trial images
                    dltk.prepareResources(
                        o.imgFiles, [ctx_sample_on, ctxs_test_on],
                        argdct.finished,    // MUST call this when successfully proloaded all resources
                        function (progress, total) {
                            var argdct2 = {progress: progress, total: total, msg: ''};
                            _callHookfunctions('onUpdatePreloadProgress', argdct2); 
                            $(argdct.elemPreload).html(argdct2.msg);   // processed text is retrived from argdct2.msg 
                        },
                        {rsrcs: rsrcs}
                    );
                },
                null,    // no progress update here
                {rsrcs: rsrcs});
            // Note: no need to call zen.preload() anymore
        };

        this.onBeginExp = function onBeginExp() {
            // Make the sample (answer) canvases clickable (This func is called by the Experiment object)
            var make_handler = function make_handler(idx) {
                return function () { _clickedTestBtn(idx); };
            };

            for (var i = 0; i < o.elemTestClickables.length; i++)
                $(o.elemTestClickables[i]).click(make_handler(i));
        };

        this.onRunNextTrialAsync = function onRunNextTrialAsync (argdct) {
            // This is called by Experiment object to procced to the next trial
            // Since this is an async function, argdct.finished() must be called upon successful
            // completion of rendering of this trial.  This is internally done inside _runTrialOnce()
            _safeRunTrialOnce(argdct);
        };

        this._updateOptions = function _updateOptions(optdct) {
            // Provides an on-the-fly way to change some options
            // This is mainly provided for debugging/diagnosis purposes.
            // Be extra careful when use this; don't use unless you know what you're doing.
            if (!defined(optdct)) return;
            o = dltk.applyDefaults(optdct, o);
        };
    };  // end of RSVPModule
}(window.dltk = window.dltk || {}, window));