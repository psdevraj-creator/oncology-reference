window.dash_clientside = window.dash_clientside || {};

window.dash_clientside.regimen = {
    filter: function(storeData, settings, modalities, biomarkers, searchTerm) {
        if (!storeData || !Array.isArray(storeData)) {
            return window.dash_clientside.no_update;
        }

        var filtered = storeData;

        if (settings && Array.isArray(settings) && settings.length) {
            filtered = filtered.filter(function(d) {
                return settings.indexOf(d.setting) !== -1;
            });
        }

        if (modalities && Array.isArray(modalities) && modalities.length) {
            filtered = filtered.filter(function(d) {
                if (!d.Modality) return false;
                var mods = d.Modality.split(', ');
                return modalities.some(function(m) {
                    return mods.indexOf(m) !== -1;
                });
            });
        }

        if (biomarkers && Array.isArray(biomarkers) && biomarkers.length) {
            filtered = filtered.filter(function(d) {
                if (!d.Biomarkers) return false;
                return biomarkers.some(function(b) {
                    return d.Biomarkers.indexOf(b) !== -1;
                });
            });
        }

        if (searchTerm && searchTerm.trim()) {
            var term = searchTerm.trim().toLowerCase();
            filtered = filtered.filter(function(d) {
                return (
                    (d.regimen_name || '').toLowerCase().indexOf(term) !== -1 ||
                    (d.setting || '').toLowerCase().indexOf(term) !== -1 ||
                    (d.Drugs || '').toLowerCase().indexOf(term) !== -1 ||
                    (d.Biomarkers || '').toLowerCase().indexOf(term) !== -1 ||
                    (d.Modality || '').toLowerCase().indexOf(term) !== -1 ||
                    (d.evidence_level || '').toLowerCase().indexOf(term) !== -1 ||
                    (d.guideline_category || '').toLowerCase().indexOf(term) !== -1
                );
            });
        }

        return filtered;
    }
};
