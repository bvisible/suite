<template>
	<transition-group
		tag="div"
		@before-enter="beforeEnter"
		@enter="enter"
		@after-enter="afterEnter"
	>
		<slot></slot>
	</transition-group>
</template>

<script setup>
const props = defineProps({
	duration: {
		type: String,
		default: 0,
	},
	skip: {
		type: Boolean,
		default: false,
	},
})

const beforeEnter = (el) => {
	if (props.skip) return

	el.style.opacity = 0
	el.style.transition = 'none'
}

const enter = (el, done) => {
	if (props.skip) return done()

	el.offsetWidth

	el.style.transition = `opacity ${props.duration}s ease-in-out`
	el.style.opacity = 1

	el.addEventListener('transitionend', done, { once: true })
}

const afterEnter = (el) => {
	if (props.skip) return

	el.style.transition = ''
}
</script>
