odoo.define('web.clock', function(require){
"use strict";

/**
 * Time is invaluable thing we have. Every second does matter.
 * 
 * 
 */

var config = require('web.config');
var core = require('web.core');
var session = require('web.session');
var SystrayMenu = require('web.SystrayMenu');
var Widget = require('web.Widget');
var AbstractWebClient = require('web.AbstractWebClient');

var _t = core._t;
var clockTemp = null;

var Clock = Widget.extend({
    template: 'Clock',
    events: {
        'click': '_onClick',
    },
    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this.isMobile = config.device.isMobile;
        this._onClick = _.debounce(this._onClick, 1500, true);
    },
    /**
     * @override
     */
    willStart: function () {
        clockTemp = this;
        return this._super();
    },
    /**
     * @override
     */
    start: function () {
      var self = this;
      this._rpc({
         model: 'res.users',
         method: 'search_read',
         domain: [['id', '=', session.uid]],
         fields: ['show_clock'],
      })
      .then(function(res) {
        res = res[0];
        if (res.show_clock) {
          setInterval(self.renderTime, 1000);
        }
      });
    	return this._super();
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClick: function (ev) {
        ev.preventDefault();
        this.analogClock = new AnalogClock(this);
        this.analogClock.appendTo($('body'));
    },
    renderTime: function(){
        this.$(".main_clock").text(clockTemp.getTime());
    },
    getTime: function() {
    	  var today = new Date();
    	  var h = today.getHours();
    	  var m = today.getMinutes();
    	  var s = today.getSeconds();
          h = this.checkTime(h);
    	  m = this.checkTime(m);
    	  s = this.checkTime(s);
    	  var time = h + ":" + m + ":" + s;
    	  return time;
    	},
    checkTime: function (i) {
    		  if (i < 10) {i = "0" + i};  // add zero in front of numbers < 10
    		  return i;
    		}
});

var AnalogClock = Widget.extend({
    template: 'AnalogClock',
    interval: setInterval(()=>{}, 99999999999),
    events: {
        'dblclick': '_onDblClick',
        'mousedown': '_moveDial',
        'mouseup': '_dropDial'
    },
    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this.isMobile = config.device.isMobile;
    },
    /**
     * @override
     */
    willStart: function () {
        return this._super();
    },
    /**
     * @override
     */
    start: function () {
      var self = this;
      var intervalTime = this.intervalTime;
      clearInterval(this.interval);
      var hasAnalog = document.querySelectorAll('.seconds-container').length > 1;
      if (hasAnalog){
        return this._super();
      }

      this._setClock();

      if (self.intervalTime == null){
        this._rpc({
           model: 'res.users',
           method: 'search_read',
           domain: [['id', '=', session.uid]],
           fields: ['show_clock_type'],
        })
        .then(function(res) {
           res = res[0];
           if (res.show_clock_type == 'mechanical'){
            self.intervalTime = 100;
            self.intervalAngle = 10000;
           }else{
            self.intervalTime = 1000;
            self.intervalAngle = 1000;
           }
           self.show_clock_type = res.show_clock_type;
           intervalTime = self.intervalTime;
           self.interval = setInterval(self.drawClock.bind(self), self.intervalTime, self.intervalAngle);
        });
      }

      window.addEventListener('focus', function (e){
          this._setClock();
      }.bind(this));

      return this._super();
    },
    secondAngle: 0,
    minuteAngle: 0,
    hourAngle: 0,
    clockSet: false,
    _setClock: function(){
        var today = new Date();
        var h = today.getHours();
        var m = today.getMinutes();
        var s = today.getSeconds();
        var ms = today.getMilliseconds();
        if (self.show_clock_type == "mechanical") {
            this.secondAngle = (s+(ms/1000))*6;
        } else {
            this.secondAngle = s*6;
        }

        this.minuteAngle = (m+s/60)*6;
        this.hourAngle = (h+this.minuteAngle/360)*30;
        if (h > 12){
          h-=12;
        }
    },
    drawClock: function(intervalAngle){
        var seconds = document.querySelectorAll('.seconds-container');
        var minutes = document.querySelectorAll('.minutes-container');
        var hours = document.querySelectorAll('.hours-container');

        this.secondAngle+=6000/intervalAngle;
        for (var i = 0; i < seconds.length; i++) {
          seconds[i].style.webkitTransform = 'rotateZ('+ this.secondAngle +'deg)';
          seconds[i].style.transform = 'rotateZ('+ this.secondAngle +'deg)';
        }

        var minuteAngleReal = this.minuteAngle+(this.secondAngle/60);
        for (var i = 0; i < minutes.length; i++) {
          minutes[i].style.webkitTransform = 'rotateZ('+ minuteAngleReal +'deg)';
          minutes[i].style.transform = 'rotateZ('+ minuteAngleReal +'deg)';
        }
        
        var hourAngleReal = this.hourAngle+(minuteAngleReal/60);
        for (var i = 0; i < hours.length; i++) {
          hours[i].style.webkitTransform = 'rotateZ('+ hourAngleReal +'deg)';
          hours[i].style.transform = 'rotateZ('+ hourAngleReal +'deg)';
        }
    },
    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onDblClick: function (ev) {
        ev.preventDefault();
        clearInterval(this.interval);
        this.$el.remove();
    },
    _moveDial: function(ev){
      var bsDiv = this.$el[0];
      var self = this;
      var x, y;
      // On mousemove use event.clientX and event.clientY to set the location of the div to the location of the cursor:
      bsDiv.onmousemove = function(event){
          x = event.clientX;
          y = event.clientY;
          if ( typeof x !== 'undefined' ){
              bsDiv.style.left = x + "px";
              bsDiv.style.top = y + "px";
          }
      };
    },
    _dropDial: function(e){
      this.$el[0].onmousemove = null;
    }
});

SystrayMenu.Items.push(Clock);
return Clock;
})