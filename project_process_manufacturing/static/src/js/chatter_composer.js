odoo.define('project_process_manufacturing.composer.Chatter', function (require) {
"use strict";

var ChatterComposer = require('mail.composer.Chatter');
var session = require('web.session');


var ChatterComposerCustom = ChatterComposer.include({
    /**
     * @override
     * @private
     * @returns {Promise}
     */
    template: 'mail.chatter.Composer.custom',
    _preprocessMessage: function () {
        var self = this;
        return new Promise(function (resolve, reject) {
            self._super().then(function (message) {
                message = _.extend(message, {
                    subtype: 'mail.mt_comment',
                    message_type: 'comment',
                    context: _.defaults({}, self.context, session.user_context),
                });

                // Subtype
                if (self.options.isLog) {
                    message.subtype = 'mail.mt_note';
                }
                // Partner_ids
                if (!self.options.isLog) {
                    var checkedSuggestedPartners = self._getCheckedSuggestedPartners();
                    self._checkSuggestedPartners(checkedSuggestedPartners).then(function (partnerIDs) {
                        message.partner_ids = (message.partner_ids || []).concat(partnerIDs);
                        // update context
                        if(self._model == "crm.lead"){
                            message.context = _.defaults({}, message.context, {
                                mail_post_autofollow: false,
                            });
                        }else{
                            message.context = _.defaults({}, message.context, {
                                mail_post_autofollow: true,
                            });
                        }
                        if (partnerIDs.length) {
                            self.trigger_up('reset_suggested_partners');
                        }
                        resolve(message);
                    });
                } else {
                    resolve(message);
                }

            });
        });
    },
    
});

return ChatterComposerCustom;

});
