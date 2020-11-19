import { expect } from 'chai'

import { toLinearVolumeScale, toLogarithmicVolumeScale } from '@/audio/volume'

describe('store/auth', () => {
    describe('toLinearVolumeScale', () => {
        describe('it should return real 0', () => {
            expect(toLinearVolumeScale(0.0)).to.equal(0.0)
        })

        describe('it should have logarithmic scale', () => {
            expect(2 * toLinearVolumeScale(0.5)).to.be.closeTo(toLinearVolumeScale(0.6), 0.001)
        })

        describe('it should return full volume', () => {
            expect(toLogarithmicVolumeScale(1.0)).to.be.closeTo(1.0, 0.001)
        })
    })

    describe('toLogarithmicVolumeScale', () => {
        describe('it should return real 0', () => {
            expect(toLogarithmicVolumeScale(0.0)).to.equal(0.0)
        })

        describe('it should have logarithmic scale', () => {
            expect(toLogarithmicVolumeScale(0.6)).to.be.closeTo(0.9261, 0.001)
            expect(toLogarithmicVolumeScale(0.7)).to.be.closeTo(0.9483, 0.001)
        })

        describe('it should return full volume', () => {
            expect(toLogarithmicVolumeScale(1.0)).to.be.closeTo(1.0, 0.001)
        })
    })
})