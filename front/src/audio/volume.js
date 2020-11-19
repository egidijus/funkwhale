
// Provides functions to convert between linear and logarithmic volume scales.
// The logarithmic volume from the UI is converted to a linear volume with a
// logarithmic function like exp(b*x)/a.
// Compare https://www.dr-lex.be/info-stuff/volumecontrols.html for how the
// values for a and b got derived.

const PARAM_A = 1000
const PARAM_B = Math.log(1000)  // ~ 6.908

function toLinearVolumeScale(v) {
    // Or as approximation:
    // return Math.pow(v, 4)
    if (v == 0.0) {
        return 0.0
    }

    return Math.min(Math.exp(PARAM_B * v) / PARAM_A, 1.0)
}

function toLogarithmicVolumeScale(v) {
    // Or as approximation:
    // return Math.exp(Math.log(v) / 4)
    if (v == 0.0) {
        return 0.0
    }

    return Math.log(v * PARAM_A) / PARAM_B
}

exports.toLinearVolumeScale = toLinearVolumeScale
exports.toLogarithmicVolumeScale = toLogarithmicVolumeScale
