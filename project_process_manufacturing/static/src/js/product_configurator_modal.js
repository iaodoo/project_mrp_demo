odoo.define('project_process_manufacturing.VariantMixin', function (require) {
    "use strict";

var concurrency = require('web.concurrency');
var core = require('web.core');
var utils = require('web.utils');
var ajax = require('web.ajax');
var _t = core._t;
var VariantMixin = require('sale.VariantMixin');


var onChangeCombination = function (ev, $parent, combination) {
        var self = this;
        var $price = $parent.find(".oe_price:first .oe_currency_value");
        var $default_price = $parent.find(".oe_default_price:first .oe_currency_value");
        var $optional_price = $parent.find(".oe_optional:first .oe_currency_value");
        $price.text(self._priceToStr(combination.price));
        $default_price.text(self._priceToStr(combination.list_price));
        
        var isCombinationPossible = true;
        debugger
        
        if(!combination.product_id){
            $parent.find('.js_add_cart_variants').css('color', 'lightcoral');
            $parent.find('.css_not_product_available').css('display', 'block');
            $parent.find('.css_not_product_description').css('display', 'block');
            $parent.find('.css_not_product_description').text(combination.display_name);
        }else{
            $parent.find('.css_not_product_available').css('display', 'none');
            $parent.find('.css_not_product_description').css('display', 'none');
            $parent.find('.js_add_cart_variants').css('color', '#666666');
        }
        if (!_.isUndefined(combination.is_combination_possible)) {
            isCombinationPossible = combination.is_combination_possible;
        }
        this._toggleDisable($parent, isCombinationPossible);

        if (combination.has_discounted_price) {
            $default_price
                .closest('.oe_website_sale')
                .addClass("discount");
            $optional_price
                .closest('.oe_optional')
                .removeClass('d-none')
                .css('text-decoration', 'line-through');
            $default_price.parent().removeClass('d-none');
        } else {
            $default_price
                .closest('.oe_website_sale')
                .removeClass("discount");
            $optional_price.closest('.oe_optional').addClass('d-none');
            $default_price.parent().addClass('d-none');
        }

        var rootComponentSelectors = [
            'tr.js_product',
            '.oe_website_sale',
            '.o_product_configurator'
        ];

        // update images only when changing product
        // or when either ids are 'false', meaning dynamic products.
        // Dynamic products don't have images BUT they may have invalid
        // combinations that need to disable the image.
        if (!combination.product_id ||
            !this.last_product_id ||
            combination.product_id !== this.last_product_id) {
            this.last_product_id = combination.product_id;
            self._updateProductImage(
                $parent.closest(rootComponentSelectors.join(', ')),
                combination.display_image,
                combination.product_id,
                combination.product_template_id,
                combination.carousel,
                isCombinationPossible
            );
        }

        $parent
            .find('.product_id')
            .first()
            .val(combination.product_id || 0)
            .trigger('change');

        $parent
            .find('.product_display_name')
            .first()
            .text(combination.display_name);

        $parent
            .find('.js_raw_price')
            .first()
            .text(combination.price)
            .trigger('change');

        this.handleCustomValues($(ev.target));
};

/**
 * Website behavior is slightly different from backend so we append
 * "_website" to URLs to lead to a different route
 *
 * @private
 * @param {string} uri The uri to adapt
 */
VariantMixin._onChangeCombination = onChangeCombination

return VariantMixin;

});
